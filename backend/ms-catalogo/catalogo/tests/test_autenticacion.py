"""Pruebas del contrato de Identidad sin depender de un servidor externo."""

import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase, override_settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from catalogo.permissions import IsBibliotecario, PuedeConsultarCatalogo


TEST_KEY = "clave-interna-catalogo-solo-para-pruebas-2026"


class VistaBibliotecario(APIView):
    permission_classes = [IsAuthenticated, IsBibliotecario]

    def get(self, request):
        return Response({"usuario_id": request.user.usuario_id})


class VistaLectura(APIView):
    permission_classes = [IsAuthenticated, PuedeConsultarCatalogo]

    def get(self, request):
        return Response({"rol": request.user.rol.nombre})


class RespuestaFalsa:
    status = 200

    def __init__(self, datos):
        if isinstance(datos, (dict, list)):
            self.body = json.dumps(datos).encode("utf-8")
        else:
            self.body = datos

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


def respuesta_identidad(rol="bibliotecario", valido=True):
    if not valido:
        return {"valido": False, "usuario": None, "expira_en": None}
    return {
        "valido": True,
        "usuario": {
            "usuario_id": 7,
            "nombre": "Persona de prueba",
            "email": "usuario@test.local",
            "rol": {
                "rol_id": 1,
                "nombre": rol,
                "limite_prestamos_activos": 5,
            },
        },
        "expira_en": "2026-11-28T12:00:00+00:00",
    }


@override_settings(
    IDENTIDAD_INTERNAL_API_KEY=TEST_KEY,
    IDENTIDAD_INTERNAL_BASE_URL="http://ms-identidad:8000",
    IDENTIDAD_HTTP_TIMEOUT_SECONDS=3,
)
class AutenticacionRemotaTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def consultar(self, vista=VistaBibliotecario, authorization="Bearer token-de-prueba"):
        cabeceras = {}
        if authorization is not None:
            cabeceras["HTTP_AUTHORIZATION"] = authorization
        return vista.as_view()(self.factory.get("/api/libros/", **cabeceras))

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_bibliotecario_autorizado_consulta_identidad(self, urlopen_mock):
        urlopen_mock.return_value = RespuestaFalsa(respuesta_identidad())
        respuesta = self.consultar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data, {"usuario_id": 7})
        solicitud = urlopen_mock.call_args.args[0]
        self.assertEqual(solicitud.get_method(), "POST")
        self.assertEqual(solicitud.full_url, "http://ms-identidad:8000/api/internal/auth/validar/")
        self.assertEqual(json.loads(solicitud.data), {"token": "token-de-prueba"})
        self.assertEqual(solicitud.get_header("X-internal-service-key"), TEST_KEY)
        self.assertEqual(urlopen_mock.call_args.kwargs["timeout"], 3)

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_sin_token_devuelve_401_y_no_llama_identidad(self, urlopen_mock):
        respuesta = self.consultar(authorization=None)
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta["WWW-Authenticate"], "Bearer")
        urlopen_mock.assert_not_called()

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_formato_bearer_invalido_devuelve_401(self, urlopen_mock):
        for cabecera in ("Bearer", "Bearer uno dos", "Bearer " + "a" * 513):
            with self.subTest(cabecera=cabecera[:30]):
                self.assertEqual(self.consultar(authorization=cabecera).status_code, 401)
        urlopen_mock.assert_not_called()

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_token_revocado_devuelve_401(self, urlopen_mock):
        urlopen_mock.return_value = RespuestaFalsa(respuesta_identidad(valido=False))
        respuesta = self.consultar()
        self.assertEqual(respuesta.status_code, 401)

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_rol_estudiante_prohibido_en_administracion(self, urlopen_mock):
        urlopen_mock.return_value = RespuestaFalsa(respuesta_identidad(rol="estudiante"))
        self.assertEqual(self.consultar().status_code, 403)

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_tres_roles_pueden_consultar_catalogo(self, urlopen_mock):
        for rol in ("bibliotecario", "estudiante", "docente"):
            with self.subTest(rol=rol):
                urlopen_mock.return_value = RespuestaFalsa(respuesta_identidad(rol=rol))
                respuesta = self.consultar(vista=VistaLectura)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.data["rol"], rol)

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_rol_desconocido_no_consulta_catalogo(self, urlopen_mock):
        urlopen_mock.return_value = RespuestaFalsa(respuesta_identidad(rol="externo"))
        self.assertEqual(self.consultar(vista=VistaLectura).status_code, 403)

    @patch("catalogo.clients.identidad_client.urlopen", side_effect=URLError("sin conexión"))
    def test_identidad_caida_devuelve_503(self, _mock):
        self.assertEqual(self.consultar().status_code, 503)

    @patch("catalogo.clients.identidad_client.urlopen", side_effect=TimeoutError("sin respuesta"))
    def test_timeout_identidad_devuelve_503(self, _mock):
        self.assertEqual(self.consultar().status_code, 503)

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_clave_interna_rechazada_devuelve_503(self, urlopen_mock):
        urlopen_mock.side_effect = HTTPError(
            "http://ms-identidad:8000/api/internal/auth/validar/", 403,
            "Prohibido", None, None,
        )
        self.assertEqual(self.consultar().status_code, 503)

    @patch("catalogo.clients.identidad_client.urlopen")
    def test_respuesta_malformada_devuelve_503(self, urlopen_mock):
        for contenido in (b"no-json", {"valido": True}, {"valido": "true"}):
            with self.subTest(contenido=contenido):
                urlopen_mock.return_value = RespuestaFalsa(contenido)
                self.assertEqual(self.consultar().status_code, 503)

    @override_settings(IDENTIDAD_INTERNAL_API_KEY="")
    @patch("catalogo.clients.identidad_client.urlopen")
    def test_sin_clave_interna_no_se_envian_solicitudes(self, urlopen_mock):
        self.assertEqual(self.consultar().status_code, 503)
        urlopen_mock.assert_not_called()
