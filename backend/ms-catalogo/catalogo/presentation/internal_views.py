"""API de lectura entre servicios: sin sesión Bearer ni acceso a otra base."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.internal_permissions import IsCatalogoInternalService
from catalogo.models import Libro
from catalogo.presentation.internal_serializers import (
    LibroInternoSerializer,
    ResolverLibrosInternoSerializer,
)


class InternalCatalogoAPIView(APIView):
    authentication_classes = []
    permission_classes = [IsCatalogoInternalService]


class LibroInternoView(InternalCatalogoAPIView):
    def get(self, request, libro_id):
        libro = Libro.objects.filter(libro_id=libro_id).first()
        if libro is None:
            return Response(
                {"detail": "Libro no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(LibroInternoSerializer(libro).data)


class ResolverLibrosInternoView(InternalCatalogoAPIView):
    def post(self, request):
        entrada = ResolverLibrosInternoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        # Preservar orden de la solicitud y evitar respuestas duplicadas.
        ids = list(dict.fromkeys(entrada.validated_data["libros_ids"]))
        libros_por_id = Libro.objects.in_bulk(ids)
        encontrados = [libros_por_id[pk] for pk in ids if pk in libros_por_id]
        faltantes = [pk for pk in ids if pk not in libros_por_id]

        return Response(
            {
                "libros": LibroInternoSerializer(encontrados, many=True).data,
                "no_encontrados": faltantes,
            },
            status=status.HTTP_200_OK,
        )
