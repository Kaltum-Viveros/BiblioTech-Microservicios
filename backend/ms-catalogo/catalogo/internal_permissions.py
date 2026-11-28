"""Autorización de consumidores REST internos de Catálogo.

La clave propia de Catálogo nunca es un token de usuario BiblioTech.
"""

from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework.permissions import BasePermission


class IsCatalogoInternalService(BasePermission):
    message = "Acceso interno no autorizado."

    def has_permission(self, request, view):
        esperada = getattr(settings, "CATALOGO_INTERNAL_API_KEY", "")
        recibida = request.headers.get("X-Internal-Service-Key", "")
        return (
            isinstance(esperada, str)
            and len(esperada) >= 16
            and isinstance(recibida, str)
            and bool(recibida)
            and constant_time_compare(recibida, esperada)
        )
