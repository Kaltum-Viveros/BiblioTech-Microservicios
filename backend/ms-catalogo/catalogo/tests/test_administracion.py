"""Regresión HTTP de administración con rol remoto de Identidad simulado."""

from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from catalogo.clients.identidad_client import (
    IdentidadNoDisponible, RolRemoto, UsuarioRemoto,
)
from catalogo.models import Autor, Categoria, Libro


def usuario_rol(nombre):
    return UsuarioRemoto(
        usuario_id=7,
        nombre="Persona de prueba",
        email="persona@bibliotech.local",
        rol=RolRemoto(rol_id=3, nombre=nombre, limite_prestamos_activos=0),
    )


class AdministracionBibliograficaAPITests(APITestCase):
    def setUp(self):
        self.autor = Autor.objects.create(nombre="Ada Lovelace", nacionalidad="Británica")
        self.categoria = Categoria.objects.create(nombre_categoria="Computación")
        self.libro = Libro.objects.create(
            titulo="Algoritmos", isbn="9780000000001"
        )
        self.libro.autores.add(self.autor)
        self.libro.categorias.add(self.categoria)
        self.parche = patch("catalogo.clients.identidad_client.IdentidadClient.validar_token")
        self.validar = self.parche.start()
        self.addCleanup(self.parche.stop)
        self.validar.return_value = usuario_rol("bibliotecario")
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token-prueba")

    def test_listados_administrativos_requieren_bibliotecario(self):
        for url in ("/api/libros/", "/api/autores/", "/api/categorias/"):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.data["count"], 1)
                self.assertEqual(len(respuesta.data["results"]), 1)

    def test_usuario_lector_no_puede_administrar(self):
        self.validar.return_value = usuario_rol("estudiante")
        for url in ("/api/libros/", "/api/autores/", "/api/categorias/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_sin_token_no_autoriza(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/libros/").status_code, 401)
        self.validar.assert_not_called()

    def test_identidad_indisponible_retorna_503(self):
        self.validar.side_effect = IdentidadNoDisponible()
        self.assertEqual(self.client.get("/api/libros/").status_code, 503)

    def test_libro_listado_y_detalle_conservan_contrato(self):
        listado = self.client.get("/api/libros/?titulo=ALGORITMOS")
        self.assertEqual(listado.status_code, 200)
        self.assertEqual(listado.data["count"], 1)
        libro = listado.data["results"][0]
        self.assertEqual(
            set(libro),
            {"libro_id", "titulo", "isbn", "fecha_publicacion", "autores", "categorias"},
        )
        self.assertEqual(libro["autores"][0]["autor_id"], self.autor.pk)
        detalle = self.client.get(f"/api/libros/{self.libro.pk}/")
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(detalle.data, libro)

    def test_libro_registro_y_patch_preservan_relaciones(self):
        respuesta = self.client.post("/api/libros/", {
            "titulo": "Programación en Python",
            "isbn": "9780000000002",
            "autor_ids": [self.autor.pk],
            "categoria_ids": [self.categoria.pk],
        }, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        libro_id = respuesta.data["libro_id"]
        modificado = self.client.patch(
            f"/api/libros/{libro_id}/", {"titulo": "Python avanzado"}, format="json"
        )
        self.assertEqual(modificado.status_code, 200, modificado.data)
        self.assertEqual(modificado.data["titulo"], "Python avanzado")
        self.assertEqual(len(modificado.data["autores"]), 1)
        self.assertEqual(len(modificado.data["categorias"]), 1)

    def test_libro_put_vacia_asociaciones_omitidas(self):
        respuesta = self.client.put(
            f"/api/libros/{self.libro.pk}/",
            {"titulo": "Algoritmos actualizados", "isbn": "9780000000001"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(respuesta.data["autores"], [])
        self.assertEqual(respuesta.data["categorias"], [])

    def test_isbn_duplicado_retorna_400(self):
        respuesta = self.client.post("/api/libros/", {
            "titulo": "Otro libro", "isbn": self.libro.isbn,
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("isbn", respuesta.data)

    def test_rechaza_campos_desconocidos(self):
        respuesta = self.client.post("/api/libros/", {
            "titulo": "Otro libro", "isbn": "9780000000003", "ejemplar_id": 9,
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("ejemplar_id", respuesta.data)

    def test_autor_registro_detalle_y_modificacion(self):
        respuesta = self.client.post("/api/autores/", {
            "nombre": "Grace Hopper", "nacionalidad": "Estadounidense",
        }, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        autor_id = respuesta.data["autor_id"]
        detalle = self.client.get(f"/api/autores/{autor_id}/")
        self.assertEqual(detalle.status_code, 200)
        self.assertIn("cantidad_libros", detalle.data)
        actualizado = self.client.patch(
            f"/api/autores/{autor_id}/", {"nombre": "Grace Murray Hopper"}, format="json"
        )
        self.assertEqual(actualizado.status_code, 200, actualizado.data)
        self.assertEqual(actualizado.data["nombre"], "Grace Murray Hopper")

    def test_categoria_registro_detalle_y_modificacion(self):
        respuesta = self.client.post("/api/categorias/", {
            "nombre_categoria": "Ingeniería",
        }, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        categoria_id = respuesta.data["categoria_id"]
        detalle = self.client.get(f"/api/categorias/{categoria_id}/")
        self.assertEqual(detalle.status_code, 200)
        self.assertIn("cantidad_libros", detalle.data)
        actualizado = self.client.patch(
            f"/api/categorias/{categoria_id}/",
            {"nombre_categoria": "Ingeniería de software"}, format="json"
        )
        self.assertEqual(actualizado.status_code, 200, actualizado.data)
        self.assertEqual(actualizado.data["nombre_categoria"], "Ingeniería de software")

    def test_listado_libros_paginar_con_10_por_defecto(self):
        Libro.objects.bulk_create([
            Libro(titulo=f"Libro adicional {i}", isbn=f"9781111111{i:03d}")
            for i in range(10)
        ])
        respuesta = self.client.get("/api/libros/?page=2")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 11)
        self.assertEqual(len(respuesta.data["results"]), 1)
        self.assertIn("next", respuesta.data)
        self.assertIn("previous", respuesta.data)

    def test_no_expone_eliminacion_libros(self):
        respuesta = self.client.delete(f"/api/libros/{self.libro.pk}/")
        self.assertEqual(respuesta.status_code, 405)

    def test_libro_inexistente_retorna_404(self):
        respuesta = self.client.get("/api/libros/999999/")
        self.assertEqual(respuesta.status_code, 404)
