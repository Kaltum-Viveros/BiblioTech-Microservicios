"""Regresión de esquema bibliográfico sin dependencias entre bases."""

from django.apps import apps
from django.db import IntegrityError, transaction
from django.test import TestCase

from catalogo.models import Autor, Categoria, CategoriaLibro, Libro, LibroAutor


class ModelosBibliograficosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Autor.objects.create(nombre="Ada Lovelace")
        cls.categoria = Categoria.objects.create(nombre_categoria="Computación")
        cls.libro = Libro.objects.create(
            titulo="Introducción a los algoritmos",
            isbn="9780000000001",
        )

    def test_solo_existen_cinco_modelos_de_negocio_en_catalogo(self):
        modelos = {modelo.__name__ for modelo in apps.get_app_config("catalogo").get_models()}
        self.assertEqual(
            modelos,
            {"Autor", "Categoria", "Libro", "LibroAutor", "CategoriaLibro"},
        )

    def test_nombres_de_tablas_compatibles_con_el_monolito(self):
        self.assertEqual(Autor._meta.db_table, "biblioteca_autor")
        self.assertEqual(Categoria._meta.db_table, "biblioteca_categoria")
        self.assertEqual(Libro._meta.db_table, "biblioteca_libro")
        self.assertEqual(LibroAutor._meta.db_table, "biblioteca_libros_autores")
        self.assertEqual(CategoriaLibro._meta.db_table, "biblioteca_categoria_libros")

    def test_relaciones_bibliograficas(self):
        LibroAutor.objects.create(libro=self.libro, autor=self.autor)
        CategoriaLibro.objects.create(libro=self.libro, categoria=self.categoria)
        self.assertEqual(list(self.libro.autores.all()), [self.autor])
        self.assertEqual(list(self.libro.categorias.all()), [self.categoria])

    def test_isbn_debe_ser_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Libro.objects.create(titulo="Duplicado", isbn=self.libro.isbn)

    def test_nombre_de_categoria_debe_ser_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Categoria.objects.create(nombre_categoria=self.categoria.nombre_categoria)

    def test_relacion_autor_libro_no_admite_duplicados(self):
        LibroAutor.objects.create(libro=self.libro, autor=self.autor)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LibroAutor.objects.create(libro=self.libro, autor=self.autor)

    def test_relacion_categoria_libro_no_admite_duplicados(self):
        CategoriaLibro.objects.create(libro=self.libro, categoria=self.categoria)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CategoriaLibro.objects.create(libro=self.libro, categoria=self.categoria)

    def test_se_pueden_conservar_ids_explicitamente_al_importar(self):
        libro = Libro.objects.create(
            libro_id=4307,
            titulo="Libro histórico",
            isbn="9780000004307",
        )
        self.assertEqual(Libro.objects.get(pk=4307), libro)

    def test_campos_opcionales_se_mantienen(self):
        self.assertIsNone(self.autor.fecha_nacimiento)
        self.assertIsNone(self.autor.nacionalidad)
        self.assertIsNone(self.libro.fecha_publicacion)
