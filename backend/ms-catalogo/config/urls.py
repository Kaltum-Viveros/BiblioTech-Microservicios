"""Rutas de salud independientes. Las rutas públicas se migrarán en CATA03."""
from django.urls import path
from catalogo.health import health_live, health_ready

urlpatterns = [
    path("health/live/", health_live, name="health-live"),
    path("health/ready/", health_ready, name="health-ready"),
]
