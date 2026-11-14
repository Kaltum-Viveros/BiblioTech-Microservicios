"""Comprobaciones de vida y conexión para Docker Compose."""

from django.db import connections
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_live(request):
    """El proceso responde sin necesitar MySQL."""

    return JsonResponse({
        "servicio": "identidad",
        "estado": "ok",
    })


@require_GET
def health_ready(request):
    """Verifica conexión con MySQL."""

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")

    except DatabaseError:
        return JsonResponse(
            {
                "servicio": "identidad",
                "estado": "no_disponible",
            },
            status=503,
        )

    return JsonResponse({
        "servicio": "identidad",
        "estado": "ok",
    })