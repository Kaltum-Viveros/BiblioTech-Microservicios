"""Rutas de salud y administración del microservicio de Catálogo."""

from django.urls import include, path
from catalogo.health import health_live, health_ready

urlpatterns = [
    path("health/live/", health_live, name="health-live"),
    path("health/ready/", health_ready, name="health-ready"),
    path("api/", include("catalogo.urls")),
]
