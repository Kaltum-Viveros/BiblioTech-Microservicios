"""Lectura bibliográfica con existencias obtenidas del servicio propietario."""

from rest_framework import serializers

from catalogo.models import Autor, Categoria, Libro


class AutorCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = ("autor_id", "nombre")


class CategoriaCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ("categoria_id", "nombre_categoria")


class LibroCatalogoSerializer(serializers.ModelSerializer):
    autores = AutorCatalogoSerializer(many=True, read_only=True)
    categorias = CategoriaCatalogoSerializer(many=True, read_only=True)
    stock_total = serializers.SerializerMethodField()
    stock_disponible = serializers.SerializerMethodField()

    class Meta:
        model = Libro
        fields = (
            "libro_id", "titulo", "isbn", "fecha_publicacion",
            "autores", "categorias", "stock_total", "stock_disponible",
        )

    def _existencia(self, libro):
        # El cliente valida cobertura completa antes de serializar.
        return self.context["existencias"][libro.pk]

    def get_stock_total(self, libro):
        return self._existencia(libro)["stock_total"]

    def get_stock_disponible(self, libro):
        return self._existencia(libro)["stock_disponible"]
