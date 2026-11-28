"""Pruebas de contrato de la API interna para Circulación."""

from django.test import override_settings
from rest_framework.test import APITestCase

from catalogo.models import Libro


CLAVE_TEST = "clave-interna-propia-catalogo-pruebas-0123456789"


@override_settings(CATALOGO_INTERNAL_API_KEY=CLAVE_TEST)
class CatalogoApiInternaTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.primero = Libro.objects.create(
            titulo="Ingeniería de software", isbn="9780000000001"
        )
        cls.segundo = Libro.objects.create(
            titulo="Bases de datos", isbn="9780000000002"
        )

    def setUp(self):
        self.client.credentials(HTTP_X_INTERNAL_SERVICE_KEY=CLAVE_TEST)

    def test_detalle_devuelve_solo_bibliografia_minima(self):
        r = self.client.get(f"/api/internal/libros/{self.primero.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            set(r.data), {"libro_id", "titulo", "isbn", "fecha_publicacion"}
        )
        self.assertEqual(r.data["libro_id"], self.primero.pk)
        self.assertEqual(r.data["titulo"], "Ingeniería de software")
        self.assertIsNone(r.data["fecha_publicacion"])

    def test_detalle_inexistente_devuelve_404(self):
        r = self.client.get("/api/internal/libros/999999/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.data, {"detail": "Libro no encontrado."})

    def test_lote_preserva_orden_y_elimina_duplicados(self):
        r = self.client.post("/api/internal/libros/resolver/", {
            "libros_ids": [self.segundo.pk, self.primero.pk, self.segundo.pk]
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            [libro["libro_id"] for libro in r.data["libros"]],
            [self.segundo.pk, self.primero.pk],
        )
        self.assertEqual(r.data["no_encontrados"], [])

    def test_lote_reporta_no_encontrados(self):
        r = self.client.post("/api/internal/libros/resolver/", {
            "libros_ids": [999999, self.primero.pk, 888888]
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([v["libro_id"] for v in r.data["libros"]], [self.primero.pk])
        self.assertEqual(r.data["no_encontrados"], [999999, 888888])

    def test_lote_vacio_devuelve_400(self):
        r = self.client.post("/api/internal/libros/resolver/", {
            "libros_ids": []
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("libros_ids", r.data)

    def test_lote_mayor_a_cien_devuelve_400(self):
        r = self.client.post("/api/internal/libros/resolver/", {
            "libros_ids": list(range(1, 102))
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("libros_ids", r.data)

    def test_lote_ids_invalidos_devuelve_400(self):
        for valor in ([-1], [0], ["abc"], [True]):
            with self.subTest(valor=valor):
                r = self.client.post("/api/internal/libros/resolver/", {
                    "libros_ids": valor
                }, format="json")
                self.assertEqual(r.status_code, 400)

    def test_lote_campo_obligatorio(self):
        r = self.client.post("/api/internal/libros/resolver/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("libros_ids", r.data)

    def test_sin_clave_retorna_403(self):
        self.client.credentials()
        self.assertEqual(
            self.client.get(f"/api/internal/libros/{self.primero.pk}/").status_code,
            403,
        )

    def test_clave_incorrecta_retorna_403(self):
        self.client.credentials(HTTP_X_INTERNAL_SERVICE_KEY="no-valida")
        self.assertEqual(
            self.client.get(f"/api/internal/libros/{self.primero.pk}/").status_code,
            403,
        )

    @override_settings(CATALOGO_INTERNAL_API_KEY="corta")
    def test_clave_configurada_demasiado_corta_retorna_403(self):
        self.assertEqual(
            self.client.get(f"/api/internal/libros/{self.primero.pk}/").status_code,
            403,
        )

    def test_token_bearer_no_sustituye_clave_interna(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token-usuario")
        self.assertEqual(
            self.client.get(f"/api/internal/libros/{self.primero.pk}/").status_code,
            403,
        )

    def test_metodos_no_permitidos_retorna_405(self):
        r1 = self.client.get("/api/internal/libros/resolver/")
        r2 = self.client.post(f"/api/internal/libros/{self.primero.pk}/", {}, format="json")
        self.assertEqual(r1.status_code, 405)
        self.assertEqual(r2.status_code, 405)
