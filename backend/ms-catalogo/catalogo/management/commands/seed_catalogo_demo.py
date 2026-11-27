"""Carga solamente bibliografía ficticia, sin usuarios ni inventario."""

from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogo.models import Autor, Categoria, CategoriaLibro, Libro, LibroAutor


TITULOS = [
    "Arquitectura de software: fundamentos",
    "Bases de datos relacionales",
    "Redes de computadoras",
    "Programación con Python",
    "Algoritmos y estructuras",
    "Ingeniería de software aplicada",
    "Matemáticas discretas",
    "Introducción a la física",
    "Historia de la ciencia",
    "Literatura contemporánea",
    "Diseño de interfaces",
    "Seguridad informática",
    "Inteligencia artificial",
    "Estadística para ingeniería",
    "Sistemas operativos",
]
AUTORES = ["Ana Rivera", "Luis Torres", "María Luna", "Carlos Vega", "Sofía Montes"]
CATEGORIAS = ["Computación", "Ingeniería", "Ciencias", "Literatura", "Diseño"]


def isbn_demo(indice):
    """Reproduce los ISBN ficticios del seed del monolito."""
    base = f"97800000{indice:04d}"
    digito = (-sum(int(n) * (1 if j % 2 == 0 else 3)
                   for j, n in enumerate(base))) % 10
    return f"{base}{digito}"


class Command(BaseCommand):
    help = "Crea 15 libros demo, sus autores y categorías, sin afectar otros servicios."

    @transaction.atomic
    def handle(self, *args, **options):
        # Evita mezclar demostración con registros reales o importados.
        esperados = {isbn_demo(i) for i in range(1, len(TITULOS) + 1)}
        if (
            Libro.objects.exclude(isbn__in=esperados).exists()
            or Autor.objects.exclude(nombre__in=AUTORES).exists()
            or Categoria.objects.exclude(nombre_categoria__in=CATEGORIAS).exists()
        ):
            raise CommandError(
                "La base contiene bibliografía ajena al seed. "
                "No mezcles datos de demostración con la importación histórica."
            )

        autores = {}
        for i, nombre in enumerate(AUTORES):
            autor, _ = Autor.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "fecha_nacimiento": date(1970 + i * 4, i + 1, 15),
                    "nacionalidad": "Mexicana",
                },
            )
            autores[nombre] = autor

        categorias = {
            nombre: Categoria.objects.get_or_create(nombre_categoria=nombre)[0]
            for nombre in CATEGORIAS
        }

        creados = 0
        for i, titulo in enumerate(TITULOS, start=1):
            fecha = date(2010 + i, (i - 1) % 12 + 1, 10)
            libro, nuevo = Libro.objects.get_or_create(
                isbn=isbn_demo(i),
                defaults={"titulo": titulo, "fecha_publicacion": fecha},
            )
            if not nuevo and (libro.titulo != titulo or libro.fecha_publicacion != fecha):
                raise CommandError(
                    f"Conflicto con ISBN de demostración {libro.isbn}; "
                    "no se modificó la bibliografía existente."
                )
            creados += int(nuevo)
            for indice in {(i - 1) % 5, i % 5}:
                LibroAutor.objects.get_or_create(
                    libro=libro, autor=autores[AUTORES[indice]]
                )
                CategoriaLibro.objects.get_or_create(
                    libro=libro, categoria=categorias[CATEGORIAS[indice]]
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seed bibliográfico aplicado: {creados} libros nuevos; "
            f"{len(TITULOS)} libros demo disponibles."
        ))
