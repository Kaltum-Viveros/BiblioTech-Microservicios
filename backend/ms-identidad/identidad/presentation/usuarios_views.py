from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from identidad.clients.circulacion_client import CirculacionNoDisponibleError
from identidad.permissions import IsBibliotecario
from identidad.presentation.usuarios_serializers import (
    RolSerializer,
    UsuarioModificacionSerializer,
    UsuarioRegistroSerializer,
    UsuarioSerializer,
)
from identidad.services.usuarios_service import (
    CambioRolNoPermitidoError,
    CorreoDuplicadoError,
    RolNoEncontradoError,
    UsuarioNoEncontradoError,
    UsuarioService,
)


class UsuariosPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class UsuariosListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsBibliotecario]

    def get(self, request):
        usuarios = UsuarioService().listar_usuarios()
        paginador = UsuariosPagination()
        pagina = paginador.paginate_queryset(usuarios, request, view=self)
        serializer = UsuarioSerializer(pagina, many=True)
        return paginador.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UsuarioRegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            usuario = UsuarioService().registrar_usuario(serializer.validated_data)
        except RolNoEncontradoError:
            raise ValidationError({"rol_id": ["El rol indicado no existe."]})
        except CorreoDuplicadoError:
            raise ValidationError({"email": ["Este correo ya está registrado."]})

        return Response(
            UsuarioSerializer(usuario).data,
            status=status.HTTP_201_CREATED,
        )


class UsuarioDetailView(APIView):
    permission_classes = [IsAuthenticated, IsBibliotecario]

    def get(self, request, usuario_id):
        try:
            usuario = UsuarioService().obtener_usuario(usuario_id)
        except UsuarioNoEncontradoError:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UsuarioSerializer(usuario).data)

    def patch(self, request, usuario_id):
        serializer = UsuarioModificacionSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            usuario = UsuarioService().modificar_usuario(
                usuario_id, serializer.validated_data
            )
        except UsuarioNoEncontradoError:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except RolNoEncontradoError:
            raise ValidationError({"rol_id": ["El rol indicado no existe."]})
        except CorreoDuplicadoError:
            raise ValidationError({"email": ["Este correo ya está registrado."]})
        except CambioRolNoPermitidoError:
            raise ValidationError({
                "rol_id": [
                    "No se puede asignar el rol de bibliotecario "
                    "mientras el usuario tenga préstamos activos."
                ]
            })
        except CirculacionNoDisponibleError:
            return Response(
                {
                    "detail": (
                        "No es posible verificar los préstamos activos "
                        "porque Circulación no está disponible. "
                        "No se guardaron cambios."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(UsuarioSerializer(usuario).data)


class RolesListView(APIView):
    permission_classes = [IsAuthenticated, IsBibliotecario]

    def get(self, request):
        roles = UsuarioService().listar_roles()
        return Response(RolSerializer(roles, many=True).data)