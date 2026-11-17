
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings

from identidad.models import Usuario
from identidad.repositories.auth_repository import (
    DjangoTokenAccesoRepository,
    DjangoUsuarioAuthRepository,
)


class CredencialesInvalidasError(Exception):
    pass


@dataclass(frozen=True)
class ResultadoInicioSesion:
    usuario: Usuario
    token: str
    expira_en: datetime


class AuthService:

    def __init__(
        self,
        usuario_repository=None,
        token_repository=None
    ):
        self.usuario_repository = (
            usuario_repository
            if usuario_repository is not None
            else DjangoUsuarioAuthRepository()
        )

        self.token_repository = (
            token_repository
            if token_repository is not None
            else DjangoTokenAccesoRepository()
        )

    def iniciar_sesion(self, email, password):
        email_normalizado = (
            email.strip().lower()
        )

        usuario = (
            self.usuario_repository
            .obtener_por_email(email_normalizado)
        )

        if (
            usuario is None
            or not usuario.check_password(password)
        ):
            raise CredencialesInvalidasError()

        token_plano, token = (
            self.token_repository.crear(
                usuario=usuario,
                duracion_horas=settings.AUTH_TOKEN_TTL_HOURS
            )
        )

        return ResultadoInicioSesion(
            usuario=usuario,
            token=token_plano,
            expira_en=token.expira_en
        )

    def cerrar_sesion(self, token):
        self.token_repository.revocar(token)
