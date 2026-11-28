"""Catálogo lector: consultas bibliográficas y stock por un contrato REST."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.clients.circulacion_client import CirculacionClient
from catalogo.models import Autor, Categoria, Libro
from catalogo.permissions import PuedeConsultarCatalogo
from catalogo.presentation.catalogo_serializers import (
    AutorCatalogoSerializer,
    CategoriaCatalogoSerializer,
    LibroCatalogoSerializer,
)


class CatalogoLecturaAPIView(APIView):
    permission_classes = [IsAuthenticated, PuedeConsultarCatalogo]


class CatalogoPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def _filtro_id(request, nombre, alternativo):
    valor = request.query_params.get(nombre)
    if valor is None:
        valor = request.query_params.get(alternativo)
    if valor is None or valor == "":
        return None
    if not valor.isdecimal() or int(valor) <= 0:
        raise ValidationError({nombre: ["Debe ser un entero positivo."]})
    return int(valor)


def _solo_disponibles(request):
    valor = request.query_params.get("solo_disponibles")
    if valor is None:
        valor = request.query_params.get("disponible")
    if valor is None:
        return False
    if valor.casefold() in ("1", "true", "si", "sí"):
        return True
    if valor.casefold() in ("0", "false", "no"):
        return False
    raise ValidationError({"solo_disponibles": ["Utiliza true/false o 1/0."]})


def _bibliografia_filtrada(request):
    libros = Libro.objects.prefetch_related("autores", "categorias")

    termino = (request.query_params.get("q") or request.query_params.get("buscar") or "").strip()
    if termino:
        libros = libros.filter(
            Q(titulo__icontains=termino)
            | Q(isbn__icontains=termino)
            | Q(autores__nombre__icontains=termino)
        ).distinct()

    titulo = (request.query_params.get("titulo") or "").strip()
    if titulo:
        libros = libros.filter(titulo__icontains=titulo)
    isbn = (request.query_params.get("isbn") or "").strip()
    if isbn:
        libros = libros.filter(isbn__icontains=isbn)

    autor_id = _filtro_id(request, "autor_id", "autor")
    categoria_id = _filtro_id(request, "categoria_id", "categoria")
    if autor_id is not None:
        libros = libros.filter(autores__autor_id=autor_id)
    if categoria_id is not None:
        libros = libros.filter(categorias__categoria_id=categoria_id)

    orden = request.query_params.get("orden", "titulo_asc")
    ordenes = {
        "titulo": ("titulo", "libro_id"),
        "titulo_asc": ("titulo", "libro_id"),
        "titulo_desc": ("-titulo", "libro_id"),
        "-titulo": ("-titulo", "libro_id"),
        "id": ("libro_id",),
        "recientes": ("-fecha_publicacion", "libro_id"),
    }
    if orden not in ordenes:
        raise ValidationError({"orden": ["Orden no reconocido."]})
    return libros.order_by(*ordenes[orden])


class CatalogoListView(CatalogoLecturaAPIView):
    def get(self, request):
        libros = _bibliografia_filtrada(request)
        client = CirculacionClient()
        existencias = {}
        if _solo_disponibles(request):
            # La disponibilidad pertenece a Circulación: solicitar todos los
            # candidatos por lotes ANTES de paginar para preservar el count.
            ids = list(libros.values_list("libro_id", flat=True))
            existencias = client.consultar_existencias(ids)
            ids_con_stock = [pk for pk in ids if existencias[pk]["stock_disponible"] > 0]
            libros = libros.filter(pk__in=ids_con_stock)

        paginador = CatalogoPagination()
        pagina = paginador.paginate_queryset(libros, request, view=self)
        ids_pagina = [libro.pk for libro in pagina]
        if not existencias:
            existencias = client.consultar_existencias(ids_pagina)
        respuesta = LibroCatalogoSerializer(
            pagina, many=True, context={"existencias": existencias}
        ).data
        return paginador.get_paginated_response(respuesta)


class CatalogoDetailView(CatalogoLecturaAPIView):
    def get(self, request, libro_id):
        libro = get_object_or_404(
            Libro.objects.prefetch_related("autores", "categorias"),
            libro_id=libro_id,
        )
        existencias = CirculacionClient().consultar_existencias([libro.pk])
        return Response(LibroCatalogoSerializer(
            libro, context={"existencias": existencias}
        ).data)


class CatalogoFiltrosView(CatalogoLecturaAPIView):
    def get(self, request):
        # Estos filtros son bibliográficos; no dependen de Circulación.
        autores = Autor.objects.order_by("nombre", "autor_id")
        categorias = Categoria.objects.order_by("nombre_categoria", "categoria_id")
        return Response({
            "autores": AutorCatalogoSerializer(autores, many=True).data,
            "categorias": CategoriaCatalogoSerializer(categorias, many=True).data,
        })
