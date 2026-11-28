"""Representación mínima y consulta por lotes para Circulación."""

from rest_framework import serializers

from catalogo.models import Libro


class LibroInternoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ("libro_id", "titulo", "isbn", "fecha_publicacion")


class ResolverLibrosInternoSerializer(serializers.Serializer):
    libros_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=True,
        allow_empty=False,
        max_length=100,
    )
