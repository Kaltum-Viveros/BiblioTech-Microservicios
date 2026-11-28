"""Contrato HTTP de catálogo y traducción de existencias desde Circulación."""

from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase

from catalogo.clients.circulacion_client import CirculacionNoDisponible
from catalogo.clients.identidad_client import (
    IdentidadNoDisponible, RolRemoto, UsuarioRemoto,
)
from catalogo.models import Autor, Categoria, Libro


def usuario(nombre_rol):
    return UsuarioRemoto(
        usuario_id=7, nombre="Pruebas", email="pruebas@bibliotech.local",
        rol=RolRemoto(rol_id=3, nombre=nombre_rol, limite_prestamos_activos=3),
    )


class CatalogoPublicoTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Autor.objects.create(nombre="Ada Lovelace")
        cls.otro_autor = Autor.objects.create(nombre="Grace Hopper")
        cls.categoria = Categoria.objects.create(nombre_categoria="Cómputo")
        cls.otra_categoria = Categoria.objects.create(nombre_categoria="Historia")
        cls.libros = []
        for indice in range(12):
            libro = Libro.objects.create(
                titulo=f"Libro {indice:02d}",
                isbn=f"978000000{indice:04d}",
            )
            libro.autores.add(cls.autor if indice < 6 else cls.otro_autor)
            libro.categorias.add(cls.categoria if indice < 8 else cls.otra_categoria)
            cls.libros.append(libro)

    def setUp(self):
        self.p_identidad = patch("catalogo.clients.identidad_client.IdentidadClient.validar_token")
        self.validar = self.p_identidad.start()
        self.addCleanup(self.p_identidad.stop)
        self.validar.return_value = usuario("estudiante")
        self.p_existencias = patch("catalogo.clients.circulacion_client.CirculacionClient.consultar_existencias")
        self.consultar = self.p_existencias.start()
        self.addCleanup(self.p_existencias.stop)
        self.consultar.side_effect = lambda ids: {
            pk: {"stock_total": 3, "stock_disponible": 0 if pk == self.libros[0].pk else 2}
            for pk in ids
        }
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token-valido")

    def test_tres_roles_pueden_listar_catalogo(self):
        for rol in ("estudiante", "docente", "bibliotecario"):
            with self.subTest(rol=rol):
                self.validar.return_value = usuario(rol)
                r = self.client.get("/api/catalogo/")
                self.assertEqual(r.status_code, 200, r.data)
                self.assertEqual(r.data["count"], 12)
                self.assertEqual(len(r.data["results"]), 10)
                self.assertIn("next", r.data)
                self.assertIn("previous", r.data)

    def test_listado_incluye_bibliografia_y_existencias(self):
        r = self.client.get("/api/catalogo/?page_size=2")
        self.assertEqual(r.status_code, 200, r.data)
        libro = r.data["results"][0]
        self.assertEqual(set(libro), {
            "libro_id", "titulo", "isbn", "fecha_publicacion",
            "autores", "categorias", "stock_total", "stock_disponible",
        })
        self.assertEqual(libro["stock_total"], 3)
        self.assertEqual(libro["stock_disponible"], 0)
        self.assertEqual(libro["autores"][0]["nombre"], "Ada Lovelace")
        self.assertEqual(libro["categorias"][0]["nombre_categoria"], "Cómputo")
        self.consultar.assert_called_once_with([l.pk for l in self.libros[:2]])

    def test_detalle_incluye_stock_y_relaciones(self):
        libro = self.libros[2]
        r = self.client.get(f"/api/catalogo/{libro.pk}/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["libro_id"], libro.pk)
        self.assertEqual(r.data["stock_disponible"], 2)
        self.assertEqual(len(r.data["autores"]), 1)
        self.consultar.assert_called_once_with([libro.pk])

    def test_detalle_inexistente_404_no_consulta_stock(self):
        self.assertEqual(self.client.get("/api/catalogo/999999/").status_code, 404)
        self.consultar.assert_not_called()

    def test_filtros_no_dependen_de_stock(self):
        r = self.client.get("/api/catalogo/filtros/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(len(r.data["autores"]), 2)
        self.assertEqual(len(r.data["categorias"]), 2)
        self.assertIn("autor_id", r.data["autores"][0])
        self.assertIn("categoria_id", r.data["categorias"][0])
        self.consultar.assert_not_called()

    def test_sin_token_devuelve_401(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/catalogo/").status_code, 401)
        self.validar.assert_not_called()
        self.consultar.assert_not_called()

    def test_rol_no_autorizado_devuelve_403(self):
        self.validar.return_value = usuario("visitante")
        self.assertEqual(self.client.get("/api/catalogo/").status_code, 403)
        self.consultar.assert_not_called()

    def test_identidad_indisponible_devuelve_503(self):
        self.validar.side_effect = IdentidadNoDisponible()
        self.assertEqual(self.client.get("/api/catalogo/").status_code, 503)
        self.consultar.assert_not_called()

    def test_circulacion_indisponible_devuelve_503_y_no_inventa_stock(self):
        self.consultar.side_effect = CirculacionNoDisponible()
        self.assertEqual(self.client.get("/api/catalogo/").status_code, 503)
        self.assertEqual(self.client.get(f"/api/catalogo/{self.libros[0].pk}/").status_code, 503)

    def test_filtrar_por_termino_en_titulo_isbn_y_autor(self):
        for termino, esperados in (
            ("Libro 03", 1),
            (self.libros[2].isbn, 1),
            ("Grace Hopper", 6),
        ):
            with self.subTest(termino=termino):
                r = self.client.get("/api/catalogo/", {"q": termino})
                self.assertEqual(r.status_code, 200, r.data)
                self.assertEqual(r.data["count"], esperados)

    def test_filtrar_por_autor_y_categoria(self):
        r = self.client.get("/api/catalogo/", {
            "autor_id": self.autor.pk, "categoria_id": self.categoria.pk,
        })
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["count"], 6)
        r = self.client.get("/api/catalogo/", {
            "autor": self.otro_autor.pk, "categoria": self.otra_categoria.pk,
        })
        self.assertEqual(r.data["count"], 4)

    def test_filtro_id_invalido_400(self):
        for valores in ({"autor_id": "abc"}, {"categoria_id": "0"}):
            with self.subTest(valores=valores):
                r = self.client.get("/api/catalogo/", valores)
                self.assertEqual(r.status_code, 400)
        self.consultar.assert_not_called()

    def test_paginacion_consulta_solo_ids_de_pagina(self):
        r = self.client.get("/api/catalogo/", {"page": 2})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["count"], 12)
        self.assertEqual(len(r.data["results"]), 2)
        self.consultar.assert_called_once_with([l.pk for l in self.libros[10:]])

    def test_orden_descendente(self):
        r = self.client.get("/api/catalogo/", {"orden": "titulo_desc", "page_size": 3})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([d["titulo"] for d in r.data["results"]], [
            "Libro 11", "Libro 10", "Libro 09",
        ])

    def test_disponibilidad_inmediata_filtra_antes_de_paginar(self):
        r = self.client.get("/api/catalogo/", {
            "solo_disponibles": "true", "page_size": 5,
        })
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["count"], 11)
        self.assertEqual(len(r.data["results"]), 5)
        self.assertTrue(all(item["stock_disponible"] > 0 for item in r.data["results"]))
        self.consultar.assert_called_once_with([l.pk for l in self.libros])

    def test_solo_disponibles_false_no_filtra(self):
        r = self.client.get("/api/catalogo/", {"solo_disponibles": "false"})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["count"], 12)
        self.consultar.assert_called_once_with([l.pk for l in self.libros[:10]])

    def test_disponibilidad_invalida_400(self):
        r = self.client.get("/api/catalogo/", {"solo_disponibles": "talvez"})
        self.assertEqual(r.status_code, 400)
        self.consultar.assert_not_called()

    def test_orden_invalido_400(self):
        r = self.client.get("/api/catalogo/", {"orden": "sql"})
        self.assertEqual(r.status_code, 400)
        self.consultar.assert_not_called()

    def test_consulta_vacia_no_llama_circulacion(self):
        r = self.client.get("/api/catalogo/", {"titulo": "no existe"})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(r.data["results"], [])
        self.consultar.assert_called_once_with([])

    def test_rutas_de_lectura_no_admiten_post(self):
        r = self.client.post("/api/catalogo/", {}, format="json")
        self.assertEqual(r.status_code, 405)
