"""Pruebas del seed bibliográfico y de la importación histórica por PK."""

import json
import tempfile
from pathlib import Path
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from catalogo.models import Autor, Categoria, CategoriaLibro, Libro, LibroAutor


class SeedBibliograficoTests(TestCase):
    def test_seed_crea_solo_bibliografia_y_es_repetible(self):
        call_command("seed_catalogo_demo", verbosity=0)
        self.assertEqual(Libro.objects.count(), 15)
        self.assertEqual(Autor.objects.count(), 5)
        self.assertEqual(Categoria.objects.count(), 5)
        self.assertEqual(LibroAutor.objects.count(), 30)
        self.assertEqual(CategoriaLibro.objects.count(), 30)

        call_command("seed_catalogo_demo", verbosity=0)
        self.assertEqual(Libro.objects.count(), 15)
        self.assertEqual(LibroAutor.objects.count(), 30)

    def test_seed_rechaza_bibliografia_ajena(self):
        Libro.objects.create(titulo="Otro libro", isbn="9789999999999")
        with self.assertRaises(CommandError):
            call_command("seed_catalogo_demo", verbosity=0)
        self.assertEqual(Libro.objects.count(), 1)
        self.assertEqual(Autor.objects.count(), 0)

    def test_seed_revierte_cambios_si_isbn_existente_es_incompatible(self):
        from catalogo.management.commands.seed_catalogo_demo import isbn_demo

        Libro.objects.create(titulo="Título distinto", isbn=isbn_demo(1))
        with self.assertRaises(CommandError):
            call_command("seed_catalogo_demo", verbosity=0)
        self.assertEqual(Libro.objects.count(), 1)
        self.assertEqual(Autor.objects.count(), 0)
        self.assertEqual(Categoria.objects.count(), 0)


class ImportacionBibliograficaTests(TestCase):
    def fixture(self):
        return [
            {"model": "biblioteca.autor", "pk": 17,
             "fields": {"nombre": "Autora histórica", "fecha_nacimiento": None,
                        "nacionalidad": "Mexicana"}},
            {"model": "biblioteca.categoria", "pk": 28,
             "fields": {"nombre_categoria": "Historia"}},
            {"model": "biblioteca.libro", "pk": 4307,
             "fields": {"titulo": "Libro histórico", "isbn": "9780000004307",
                        "fecha_publicacion": "2020-05-20"}},
            {"model": "biblioteca.libroautor", "pk": 88,
             "fields": {"autor": 17, "libro": 4307}},
            {"model": "biblioteca.categorialibro", "pk": 99,
             "fields": {"categoria": 28, "libro": 4307}},
        ]

    def importar(self, datos):
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "bibliografia.json"
            archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
            call_command("importar_bibliografia", str(archivo), verbosity=0)

    def test_conserva_ids_y_relaciones_y_se_puede_repetir(self):
        self.importar(self.fixture())
        libro = Libro.objects.get(libro_id=4307)
        self.assertEqual(libro.fecha_publicacion.isoformat(), "2020-05-20")
        self.assertEqual(list(libro.autores.values_list("autor_id", flat=True)), [17])
        self.assertEqual(list(libro.categorias.values_list("categoria_id", flat=True)), [28])
        self.assertEqual(LibroAutor.objects.get(pk=88).libro_id, 4307)
        self.importar(self.fixture())
        self.assertEqual(Libro.objects.count(), 1)
        self.assertEqual(LibroAutor.objects.count(), 1)

    def test_rechaza_conflicto_de_id_sin_sobrescribir(self):
        self.importar(self.fixture())
        nuevos = self.fixture()
        nuevos[2]["fields"]["titulo"] = "Otro título"
        with self.assertRaises(CommandError):
            self.importar(nuevos)
        self.assertEqual(Libro.objects.get(pk=4307).titulo, "Libro histórico")

    def test_fallo_en_relacion_revierte_importacion_completa(self):
        datos = self.fixture()
        datos[-1]["fields"]["libro"] = 99999
        with self.assertRaises(CommandError):
            self.importar(datos)
        self.assertEqual(Libro.objects.count(), 0)
        self.assertEqual(Autor.objects.count(), 0)

    def test_rechaza_modelos_ajenos_a_catalogo(self):
        datos = self.fixture()
        datos.append({"model": "biblioteca.prestamo", "pk": 1, "fields": {}})
        with self.assertRaises(CommandError):
            self.importar(datos)
        self.assertEqual(Libro.objects.count(), 0)

    def test_rechaza_ids_duplicados_en_el_archivo(self):
        datos = self.fixture()
        datos.append(datos[0].copy())
        with self.assertRaises(CommandError):
            self.importar(datos)

    def test_rechaza_isbn_duplicado_con_id_distinto(self):
        datos = self.fixture()
        datos.append({"model": "biblioteca.libro", "pk": 123,
                      "fields": {"titulo": "Copia", "isbn": "9780000004307"}})
        with self.assertRaises(CommandError):
            self.importar(datos)
        self.assertEqual(Libro.objects.count(), 0)

    def test_importar_desde_stdin_conserva_claves(self):
        contenido = StringIO(json.dumps(self.fixture(), ensure_ascii=False))
        with patch("sys.stdin", contenido):
            call_command("importar_bibliografia", "-", verbosity=0)
        self.assertTrue(Libro.objects.filter(pk=4307).exists())

    def test_solo_validar_no_escribe_registros(self):
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "bibliografia.json"
            archivo.write_text(json.dumps(self.fixture()), encoding="utf-8")
            call_command("importar_bibliografia", str(archivo), solo_validar=True, verbosity=0)
        self.assertEqual(Libro.objects.count(), 0)
        self.assertEqual(Autor.objects.count(), 0)

    def test_fallo_en_categoria_duplicada_revierte_todo(self):
        datos = self.fixture()
        datos.append({
            "model": "biblioteca.categoria", "pk": 29,
            "fields": {"nombre_categoria": "Historia"},
        })
        with self.assertRaises(CommandError):
            self.importar(datos)
        self.assertEqual(Categoria.objects.count(), 0)
        self.assertEqual(Libro.objects.count(), 0)

    def test_fallo_en_relacion_duplicada_revierte_todo(self):
        datos = self.fixture()
        datos.append({
            "model": "biblioteca.libroautor", "pk": 89,
            "fields": {"autor": 17, "libro": 4307},
        })
        with self.assertRaises(CommandError):
            self.importar(datos)
        self.assertEqual(LibroAutor.objects.count(), 0)
        self.assertEqual(Libro.objects.count(), 0)
