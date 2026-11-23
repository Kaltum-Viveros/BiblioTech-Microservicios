
from django.utils import timezone

from identidad.models import Usuario

from identidad.repositories.auth_repository import (
    DjangoTokenAccesoRepository,
)


class InternalIdentityService:
    """
    Casos de uso que Identidad expone a otros
    microservicios mediante contratos REST.
    """

    def __init__(self, token_repository=None):
        self.token_repository = (
            token_repository
            if token_repository is not None
            else DjangoTokenAccesoRepository()
        )

    def validar_token(self, token_plano):
        """
        Devuelve el registro TokenAcceso si está vigente.

        Un token inexistente, revocado o expirado
        se considera inválido.
        """
        token = (
            self.token_repository
            .obtener_por_token_plano(token_plano)
        )

        if token is None:
            return None

        if token.expira_en <= timezone.now():
            self.token_repository.revocar(token)
            return None

        return token

    def obtener_usuario(self, usuario_id):
        return (
            Usuario.objects
            .select_related("rol")
            .filter(usuario_id=usuario_id)
            .first()
        )

    def resolver_usuarios(self, usuarios_ids):
        """
        Resuelve varios identificadores en una consulta.

        Conserva el orden recibido y elimina duplicados.
        Los identificadores inexistentes no se incluyen
        en la lista de usuarios devueltos.
        """
        ids_unicos = list(dict.fromkeys(usuarios_ids))

        encontrados = (
            Usuario.objects
            .select_related("rol")
            .filter(usuario_id__in=ids_unicos)
        )

        por_id = {
            usuario.usuario_id: usuario
            for usuario in encontrados
        }

        usuarios = [
            por_id[usuario_id]
            for usuario_id in ids_unicos
            if usuario_id in por_id
        ]

        no_encontrados = [
            usuario_id
            for usuario_id in ids_unicos
            if usuario_id not in por_id
        ]

        return usuarios, no_encontrados
