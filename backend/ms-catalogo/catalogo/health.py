"""Healthchecks del microservicio; la API de negocio vendrá después."""
from django.db import connections
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_live(request):
    return JsonResponse({"servicio": "catalogo", "estado": "ok"})


@require_GET
def health_ready(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse(
            {"servicio": "catalogo", "estado": "no_disponible"},
            status=503,
        )
    return JsonResponse({"servicio": "catalogo", "estado": "ok"})
