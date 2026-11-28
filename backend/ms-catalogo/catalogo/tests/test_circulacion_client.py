"""Pruebas de contrato y de fallos explícitos del cliente de existencias."""

import json
from unittest.mock import patch
from urllib.error import URLError

from django.test import SimpleTestCase, override_settings

from catalogo.clients.circulacion_client import (
    CirculacionClient, CirculacionNoDisponible,
)


CLAVE = "clave-interna-circulacion-solo-de-prueba-0123456789"


class RespuestaFalsa:
    status = 200

    def __init__(self, datos):
        self.datos = datos

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limite=None):
        return json.dumps(self.datos).encode("utf-8")


@override_settings(
    CIRCULACION_INTERNAL_BASE_URL="http://ms-circulacion:8000",
    CIRCULACION_INTERNAL_API_KEY=CLAVE,
    CIRCULACION_HTTP_TIMEOUT_SECONDS=2,
)
class CirculacionClientTests(SimpleTestCase):
    def test_solicitud_http_usa_ruta_clave_y_body_correctos(self):
        with patch("catalogo.clients.circulacion_client.urlopen") as abrir:
            abrir.return_value = RespuestaFalsa({"existencias": [
                {"libro_id": 7, "stock_total": 4, "stock_disponible": 2},
            ]})
            obtenido = CirculacionClient().consultar_existencias([7, 7])
            self.assertEqual(obtenido[7], {"stock_total": 4, "stock_disponible": 2})
            solicitud = abrir.call_args.args[0]
            self.assertEqual(solicitud.full_url, "http://ms-circulacion:8000/api/internal/existencias/consultar/")
            self.assertEqual(solicitud.get_method(), "POST")
            self.assertEqual(json.loads(solicitud.data), {"libros_ids": [7]})
            self.assertEqual(solicitud.get_header("X-internal-service-key"), CLAVE)
            self.assertEqual(abrir.call_args.kwargs["timeout"], 2)

    def test_vacio_no_hace_http(self):
        with patch("catalogo.clients.circulacion_client.urlopen") as abrir:
            self.assertEqual(CirculacionClient().consultar_existencias([]), {})
            abrir.assert_not_called()

    def test_agrupa_lotes_de_100(self):
        with patch("catalogo.clients.circulacion_client.urlopen") as abrir:
            def atender(solicitud, timeout):
                ids = json.loads(solicitud.data)["libros_ids"]
                return RespuestaFalsa({"existencias": [
                    {"libro_id": pk, "stock_total": 1, "stock_disponible": 0}
                    for pk in ids
                ]})
            abrir.side_effect = atender
            resultado = CirculacionClient().consultar_existencias(list(range(1, 206)))
            self.assertEqual(len(resultado), 205)
            self.assertEqual(abrir.call_count, 3)

    @override_settings(CIRCULACION_INTERNAL_API_KEY="")
    def test_sin_clave_falla_sin_solicitud(self):
        with patch("catalogo.clients.circulacion_client.urlopen") as abrir:
            with self.assertRaises(CirculacionNoDisponible):
                CirculacionClient().consultar_existencias([1])
            abrir.assert_not_called()

    def test_no_inventa_ceros_si_omiten_id(self):
        with patch("catalogo.clients.circulacion_client.urlopen", return_value=RespuestaFalsa({"existencias": []})):
            with self.assertRaises(CirculacionNoDisponible):
                CirculacionClient().consultar_existencias([1])

    def test_rechaza_stock_invalido(self):
        for total, disponible in ((-1, 0), (1, 2), (True, 0), (1, False)):
            with self.subTest(total=total, disponible=disponible):
                with patch("catalogo.clients.circulacion_client.urlopen", return_value=RespuestaFalsa({
                    "existencias": [{"libro_id": 1, "stock_total": total, "stock_disponible": disponible}],
                })):
                    with self.assertRaises(CirculacionNoDisponible):
                        CirculacionClient().consultar_existencias([1])

    def test_rechaza_ids_extra_y_duplicados(self):
        for datos in (
            [{"libro_id": 2, "stock_total": 1, "stock_disponible": 1}],
            [{"libro_id": 1, "stock_total": 1, "stock_disponible": 1}] * 2,
        ):
            with self.subTest(datos=datos):
                with patch("catalogo.clients.circulacion_client.urlopen", return_value=RespuestaFalsa({"existencias": datos})):
                    with self.assertRaises(CirculacionNoDisponible):
                        CirculacionClient().consultar_existencias([1])

    def test_timeout_o_caida_devuelve_503(self):
        with patch("catalogo.clients.circulacion_client.urlopen", side_effect=URLError("caída")):
            with self.assertRaises(CirculacionNoDisponible) as caso:
                CirculacionClient().consultar_existencias([1])
        self.assertEqual(caso.exception.status_code, 503)

    def test_rechaza_ids_no_enteros_positivos(self):
        for valores in ([True], [0], [-1], ["1"]):
            with self.subTest(valores=valores):
                with self.assertRaises(ValueError):
                    CirculacionClient().consultar_existencias(valores)
