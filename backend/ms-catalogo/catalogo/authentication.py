"""Autenticación Bearer opaca, delegada a Identidad por HTTP interno."""

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from catalogo.clients.identidad_client import IdentidadClient


class CatalogoTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        partes = get_authorization_header(request).split()
        if not partes or partes[0].lower() != b"bearer":
            return None

        if len(partes) != 2:
            raise AuthenticationFailed("Formato de autorización inválido.")

        try:
            token = partes[1].decode("utf-8")
        except UnicodeDecodeError:
            raise AuthenticationFailed("Token inválido.") from None

        if not token or len(token) > 512:
            raise AuthenticationFailed("Token inválido.")

        usuario = IdentidadClient().validar_token(token)
        if usuario is None:
            raise AuthenticationFailed("Token inválido, expirado o revocado.")

        # auth conserva el token plano en memoria para esta petición; no se registra.
        return usuario, token

    def authenticate_header(self, request):
        return "Bearer"
