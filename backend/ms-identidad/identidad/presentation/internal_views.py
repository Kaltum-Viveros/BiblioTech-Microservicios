
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from identidad.internal_permissions import IsInternalService

from identidad.presentation.auth_serializers import (
    UsuarioSesionSerializer,
)

from identidad.presentation.internal_serializers import (
    ResolverUsuariosInternoSerializer,
    ValidarTokenInternoSerializer,
)

from identidad.services.internal_service import (
    InternalIdentityService,
)


class InternalAPIView(APIView):
    """
    Clase base de los endpoints internos.

    No usa sesiones de usuario para autenticar
    al microservicio que realiza la solicitud.
    """

    authentication_classes = []
    permission_classes = [IsInternalService]


class ValidarTokenInternoView(InternalAPIView):

    def post(self, request):
        serializer = ValidarTokenInternoSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        service = InternalIdentityService()

        token = service.validar_token(
            serializer.validated_data["token"]
        )

        if token is None:
            return Response(
                {
                    "valido": False,
                    "usuario": None,
                    "expira_en": None,
                },
                status=status.HTTP_200_OK
            )

        usuario_data = UsuarioSesionSerializer(
            token.usuario
        ).data

        return Response(
            {
                "valido": True,
                "usuario": usuario_data,
                "expira_en": token.expira_en.isoformat(),
            },
            status=status.HTTP_200_OK
        )


class UsuarioInternoView(InternalAPIView):

    def get(self, request, usuario_id):
        service = InternalIdentityService()

        usuario = service.obtener_usuario(
            usuario_id
        )

        if usuario is None:
            return Response(
                {
                    "detail": "Usuario no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            UsuarioSesionSerializer(usuario).data,
            status=status.HTTP_200_OK
        )


class ResolverUsuariosInternoView(InternalAPIView):

    def post(self, request):
        serializer = ResolverUsuariosInternoSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        service = InternalIdentityService()

        usuarios, no_encontrados = (
            service.resolver_usuarios(
                serializer.validated_data["usuarios_ids"]
            )
        )

        return Response(
            {
                "usuarios": UsuarioSesionSerializer(
                    usuarios,
                    many=True
                ).data,
                "no_encontrados": no_encontrados,
            },
            status=status.HTTP_200_OK
        )
