
from django.conf import settings
from django.utils.crypto import constant_time_compare

from rest_framework.permissions import BasePermission


class IsInternalService(BasePermission):
    """
    Autoriza solicitudes REST entre microservicios.

    Utiliza una clave compartida configurada
    mediante IDENTIDAD_INTERNAL_API_KEY.

    La longitud mínima de 16 caracteres se utiliza
    únicamente para nuestro entorno de desarrollo.
    """

    message = "Acceso interno no autorizado."

    def has_permission(self, request, view):
        clave_esperada = getattr(
            settings,
            "IDENTIDAD_INTERNAL_API_KEY",
            ""
        )

        clave_recibida = request.headers.get(
            "X-Internal-Service-Key",
            ""
        )

        if not isinstance(clave_esperada, str):
            return False

        if not isinstance(clave_recibida, str):
            return False

        # Permite nuestra clave fija de desarrollo.
        if len(clave_esperada) < 16:
            return False

        if not clave_recibida:
            return False

        return constant_time_compare(
            clave_recibida,
            clave_esperada
        )
