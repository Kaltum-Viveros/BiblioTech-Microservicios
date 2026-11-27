"""Rutas públicas administrativas del monolito, sin rutas de Circulación."""

from django.urls import path

from catalogo.presentation.libros_views import LibrosListCreateView, LibroDetailView
from catalogo.presentation.autores_views import AutoresListCreateView, AutorDetailView
from catalogo.presentation.categorias_views import CategoriasListCreateView, CategoriaDetailView


urlpatterns = [
    path("libros/", LibrosListCreateView.as_view(), name="libros-list-create"),
    path("libros/<int:libro_id>/", LibroDetailView.as_view(), name="libros-detail"),
    path("autores/", AutoresListCreateView.as_view(), name="autores-list-create"),
    path("autores/<int:autor_id>/", AutorDetailView.as_view(), name="autores-detail"),
    path("categorias/", CategoriasListCreateView.as_view(), name="categorias-list-create"),
    path("categorias/<int:categoria_id>/", CategoriaDetailView.as_view(), name="categorias-detail"),
]
