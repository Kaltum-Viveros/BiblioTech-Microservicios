
"""C07: pruebas HTTP del gateway real de BiblioTech.

Ejecutar desde la raiz del repositorio:

docker compose exec -e GATEWAY_TEST_PASSWORD="Biblioteca123*" \
    ms-identidad python scripts/verificar_gateway.py

Las pruebas se ejecutan en ms-identidad, conectado a la red Docker api.
El Host localhost:8000 reproduce las solicitudes del navegador Angular.
Las sesiones de prueba se revocan al finalizar.
"""

import json
import os
import unittest

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GATEWAY_URL = os.getenv(
    "GATEWAY_TEST_URL",
    "http://api_gateway"
).rstrip("/")

PUBLIC_HOST = os.getenv(
    "GATEWAY_TEST_HOST",
    "localhost:8000"
)

PASSWORD = os.getenv(
    "GATEWAY_TEST_PASSWORD",
    ""
)

ANGULAR_ORIGIN = "http://localhost:4200"


class Respuesta:

    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.raw = body

        try:
            self.data = (
                json.loads(body.decode("utf-8"))
                if body else None
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.data = None


def llamar(
    metodo,
    ruta,
    *,
    token=None,
    datos=None,
    headers=None,
):
    cabeceras = {
        "Host": PUBLIC_HOST,
        "Accept": "application/json",
    }

    if token:
        cabeceras["Authorization"] = f"Bearer {token}"

    if headers:
        cabeceras.update(headers)

    cuerpo = None

    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"

    solicitud = Request(
        f"{GATEWAY_URL}{ruta}",
        data=cuerpo,
        headers=cabeceras,
        method=metodo,
    )

    try:
        with urlopen(solicitud, timeout=10) as respuesta:
            return Respuesta(
                respuesta.status,
                respuesta.headers,
                respuesta.read(),
            )

    except HTTPError as error:
        return Respuesta(
            error.code,
            error.headers,
            error.read(),
        )

    except URLError as error:
        raise AssertionError(
            f"No se pudo acceder al gateway: {error.reason}"
        ) from error


class GatewayC07Tests(unittest.TestCase):

    tokens = {}
    usuarios = {}

    @classmethod
    def setUpClass(cls):
        if not PASSWORD:
            raise RuntimeError(
                "Define GATEWAY_TEST_PASSWORD "
                "con la contraseña del seed."
            )

        cuentas = {
            "estudiante": "esme@bibliotech.com",
            "docente": "saul@bibliotech.com",
            "bibliotecario": "kalt@bibliotech.com",
        }

        try:
            for rol, email in cuentas.items():
                respuesta = llamar(
                    "POST",
                    "/api/auth/login/",
                    datos={
                        "email": email,
                        "password": PASSWORD,
                    },
                )

                if (
                    respuesta.status != 200
                    or not isinstance(respuesta.data, dict)
                ):
                    raise AssertionError(
                        f"No se pudo iniciar sesion como {rol}: "
                        f"HTTP {respuesta.status}"
                    )

                if respuesta.data.get("tipo_token") != "Bearer":
                    raise AssertionError(
                        f"Login de {rol} no devuelve Bearer"
                    )

                if (
                    respuesta.data["usuario"]["rol"]["nombre"]
                    != rol
                ):
                    raise AssertionError(
                        f"El seed de {rol} tiene un rol inesperado"
                    )

                cls.tokens[rol] = respuesta.data["token"]
                cls.usuarios[rol] = respuesta.data["usuario"]

        except Exception:
            cls._revocar_todos()
            raise

    @classmethod
    def _revocar_todos(cls):
        for token in cls.tokens.values():
            try:
                llamar(
                    "POST",
                    "/api/auth/logout/",
                    token=token,
                    datos={},
                )
            except Exception:
                pass

        cls.tokens.clear()

    @classmethod
    def tearDownClass(cls):
        cls._revocar_todos()

    def probar_estado(
        self,
        metodo,
        ruta,
        esperado,
        **kwargs,
    ):
        respuesta = llamar(
            metodo,
            ruta,
            **kwargs,
        )

        self.assertEqual(
            respuesta.status,
            esperado,
            (
                f"{metodo} {ruta}: "
                f"{respuesta.raw[:250]!r}"
            ),
        )

        return respuesta

    # =========================================
    # 01. HEALTH LIVE
    # =========================================

    def test_01_live(self):
        respuesta = self.probar_estado(
            "GET",
            "/health/live/",
            200,
        )

        self.assertEqual(
            respuesta.data,
            {
                "servicio": "identidad",
                "estado": "ok",
            },
        )

    # =========================================
    # 02. HEALTH READY
    # =========================================

    def test_02_ready(self):
        respuesta = self.probar_estado(
            "GET",
            "/health/ready/",
            200,
        )

        self.assertEqual(
            respuesta.data,
            {
                "servicio": "identidad",
                "estado": "ok",
            },
        )

    # =========================================
    # 03. LOGIN CON PASSWORD INCORRECTA
    # =========================================

    def test_03_login_incorrecto_no_revela_usuario(self):
        respuesta = self.probar_estado(
            "POST",
            "/api/auth/login/",
            401,
            datos={
                "email": "esme@bibliotech.com",
                "password": "incorrecta",
            },
        )

        self.assertNotIn(
            "token",
            respuesta.data,
        )

    # =========================================
    # 04. LOGIN INCOMPLETO
    # =========================================

    def test_04_login_incompleto(self):
        respuesta = self.probar_estado(
            "POST",
            "/api/auth/login/",
            400,
            datos={
                "email": "esme@bibliotech.com",
            },
        )

        self.assertIn(
            "password",
            respuesta.data,
        )

    # =========================================
    # 05. SESION DE LOS TRES ROLES
    # =========================================

    def test_05_me_de_los_tres_roles(self):
        for rol, token in self.tokens.items():
            with self.subTest(rol=rol):
                respuesta = self.probar_estado(
                    "GET",
                    "/api/auth/me/",
                    200,
                    token=token,
                )

                self.assertEqual(
                    respuesta.data["usuario_id"],
                    self.usuarios[rol]["usuario_id"],
                )

                self.assertEqual(
                    respuesta.data["rol"]["nombre"],
                    rol,
                )

    # =========================================
    # 06. PERMISO DE LECTOR
    # =========================================

    def test_06_lector_permitido_a_estudiante_y_docente(self):
        for rol in ("estudiante", "docente"):
            with self.subTest(rol=rol):
                self.probar_estado(
                    "GET",
                    "/api/auth/access/lector/",
                    200,
                    token=self.tokens[rol],
                )

        self.probar_estado(
            "GET",
            "/api/auth/access/lector/",
            403,
            token=self.tokens["bibliotecario"],
        )

    # =========================================
    # 07. PERMISO DE BIBLIOTECARIO
    # =========================================

    def test_07_bibliotecario_restringido_por_rol(self):
        self.probar_estado(
            "GET",
            "/api/auth/access/bibliotecario/",
            200,
            token=self.tokens["bibliotecario"],
        )

        for rol in ("estudiante", "docente"):
            with self.subTest(rol=rol):
                self.probar_estado(
                    "GET",
                    "/api/auth/access/bibliotecario/",
                    403,
                    token=self.tokens[rol],
                )

    # =========================================
    # 08. LISTADO DE USUARIOS
    # =========================================

    def test_08_usuarios_solo_bibliotecario(self):
        respuesta = self.probar_estado(
            "GET",
            "/api/usuarios/?page=1&page_size=2",
            200,
            token=self.tokens["bibliotecario"],
        )

        self.assertIn(
            "count",
            respuesta.data,
        )

        self.assertIn(
            "results",
            respuesta.data,
        )

        self.assertLessEqual(
            len(respuesta.data["results"]),
            2,
        )

        for rol in ("estudiante", "docente"):
            self.probar_estado(
                "GET",
                "/api/usuarios/",
                403,
                token=self.tokens[rol],
            )

    # =========================================
    # 09. LISTADO DE ROLES
    # =========================================

    def test_09_roles_solo_bibliotecario(self):
        respuesta = self.probar_estado(
            "GET",
            "/api/roles/",
            200,
            token=self.tokens["bibliotecario"],
        )

        self.assertEqual(
            {
                rol["nombre"]
                for rol in respuesta.data
            },
            {
                "estudiante",
                "docente",
                "bibliotecario",
            },
        )

        for rol in ("estudiante", "docente"):
            self.probar_estado(
                "GET",
                "/api/roles/",
                403,
                token=self.tokens[rol],
            )

    # =========================================
    # 10. DETALLE DE USUARIO
    # =========================================

    def test_10_detalle_usuario_y_permiso(self):
        usuario_id = (
            self.usuarios["bibliotecario"]["usuario_id"]
        )

        ruta = f"/api/usuarios/{usuario_id}/"

        respuesta = self.probar_estado(
            "GET",
            ruta,
            200,
            token=self.tokens["bibliotecario"],
        )

        self.assertEqual(
            respuesta.data["usuario_id"],
            usuario_id,
        )

        self.probar_estado(
            "GET",
            ruta,
            403,
            token=self.tokens["estudiante"],
        )

        self.probar_estado(
            "GET",
            "/api/usuarios/999999/",
            404,
            token=self.tokens["bibliotecario"],
        )

    # =========================================
    # 11. PATCH Y CAMPO PROHIBIDO
    # =========================================

    def test_11_patch_idempotente_y_campo_prohibido(self):
        usuario = self.usuarios["bibliotecario"]
        ruta = f"/api/usuarios/{usuario['usuario_id']}/"

        # Se guarda el mismo nombre para no alterar
        # funcionalmente los datos del seed.
        respuesta = self.probar_estado(
            "PATCH",
            ruta,
            200,
            token=self.tokens["bibliotecario"],
            datos={
                "nombre": usuario["nombre"],
            },
        )

        self.assertEqual(
            respuesta.data["nombre"],
            usuario["nombre"],
        )

        respuesta = self.probar_estado(
            "PATCH",
            ruta,
            400,
            token=self.tokens["bibliotecario"],
            datos={
                "password": "campo-no-permitido",
            },
        )

        self.assertIn(
            "password",
            respuesta.data,
        )

        self.probar_estado(
            "PATCH",
            ruta,
            403,
            token=self.tokens["estudiante"],
            datos={},
        )

    # =========================================
    # 12. POST INVALIDO
    # =========================================

    def test_12_post_usuario_invalido_sin_crearlo(self):
        respuesta = self.probar_estado(
            "POST",
            "/api/usuarios/",
            400,
            token=self.tokens["bibliotecario"],
            datos={
                "nombre": "Usuario sin datos",
            },
        )

        self.assertIn(
            "email",
            respuesta.data,
        )

        self.probar_estado(
            "POST",
            "/api/usuarios/",
            403,
            token=self.tokens["estudiante"],
            datos={},
        )

    # =========================================
    # 13. SIN AUTENTICACION
    # =========================================

    def test_13_sin_autenticacion(self):
        for ruta in (
            "/api/auth/me/",
            "/api/roles/",
            "/api/usuarios/",
        ):
            with self.subTest(ruta=ruta):
                self.probar_estado(
                    "GET",
                    ruta,
                    401,
                )

    # =========================================
    # 14. PREFLIGHT CORS DE ANGULAR
    # =========================================

    def test_14_preflight_cors_angular(self):
        casos = (
            (
                "/api/auth/login/",
                "POST",
            ),
            (
                "/api/usuarios/",
                "POST",
            ),
            (
                (
                    "/api/usuarios/"
                    f"{self.usuarios['bibliotecario']['usuario_id']}/"
                ),
                "PATCH",
            ),
        )

        for ruta, metodo in casos:
            with self.subTest(ruta=ruta):
                respuesta = self.probar_estado(
                    "OPTIONS",
                    ruta,
                    200,
                    headers={
                        "Origin": ANGULAR_ORIGIN,
                        "Access-Control-Request-Method": metodo,
                        "Access-Control-Request-Headers": (
                            "authorization,content-type"
                        ),
                    },
                )

                self.assertEqual(
                    respuesta.headers.get(
                        "Access-Control-Allow-Origin"
                    ),
                    ANGULAR_ORIGIN,
                )

                self.assertIn(
                    metodo,
                    respuesta.headers.get(
                        "Access-Control-Allow-Methods",
                        "",
                    ),
                )

    # =========================================
    # 15. CORS EN RESPUESTA DE ERROR
    # =========================================

    def test_15_cors_en_respuesta_403(self):
        respuesta = self.probar_estado(
            "GET",
            "/api/roles/",
            403,
            token=self.tokens["estudiante"],
            headers={
                "Origin": ANGULAR_ORIGIN,
            },
        )

        self.assertEqual(
            respuesta.headers.get(
                "Access-Control-Allow-Origin"
            ),
            ANGULAR_ORIGIN,
        )

    # =========================================
    # 16. BLOQUEO DE API INTERNA
    # =========================================

    def test_16_api_interna_bloqueada_con_y_sin_clave(self):
        key = os.getenv(
            "IDENTIDAD_INTERNAL_API_KEY",
            "",
        )

        self.probar_estado(
            "GET",
            "/api/internal/usuarios/1/",
            404,
        )

        self.probar_estado(
            "GET",
            "/api/internal/usuarios/1/",
            404,
            headers={
                "X-Internal-Service-Key": key,
            },
        )

        for ruta in (
            "/api/internal",
            "/internal/usuarios/1/",
        ):
            self.probar_estado(
                "GET",
                ruta,
                404,
            )

    # =========================================
    # 17. RUTAS SIN MICROSERVICIO
    # =========================================

    def test_17_rutas_no_implementadas_no_van_a_identidad(self):
        for ruta in (
            "/",
            "/api/",
            "/api/catalogo/",
            "/api/prestamos/",
            "/api/libros/",
            "/api/auth/otra/",
            "/api/usuarios/1/editar/",
        ):
            with self.subTest(ruta=ruta):
                respuesta = self.probar_estado(
                    "GET",
                    ruta,
                    404,
                )

                self.assertEqual(
                    respuesta.data.get("detail"),
                    "Ruta no disponible en el gateway.",
                )

    # =========================================
    # 18. ERROR 503 DEL BACKEND
    # =========================================

    def test_18_error_503_circulacion_se_conserva(self):
        # C05 bloquea una promocion a bibliotecario
        # cuando Circulacion no puede confirmar
        # la ausencia de prestamos activos.

        estudiante_id = (
            self.usuarios["estudiante"]["usuario_id"]
        )

        bibliotecario_rol_id = (
            self.usuarios["bibliotecario"]["rol"]["rol_id"]
        )

        ruta = f"/api/usuarios/{estudiante_id}/"

        respuesta = self.probar_estado(
            "PATCH",
            ruta,
            503,
            token=self.tokens["bibliotecario"],
            datos={
                "rol_id": bibliotecario_rol_id,
            },
        )

        self.assertIn(
            "Circulaci",
            respuesta.data["detail"],
        )

        # Verificar que la modificación fue rechazada.
        usuario = self.probar_estado(
            "GET",
            ruta,
            200,
            token=self.tokens["bibliotecario"],
        )

        self.assertEqual(
            usuario.data["rol"]["nombre"],
            "estudiante",
        )

    # =========================================
    # 19. LOGOUT Y REVOCACION
    # =========================================

    def test_19_logout_revoca_token_y_me_devuelve_401(self):
        login = self.probar_estado(
            "POST",
            "/api/auth/login/",
            200,
            datos={
                "email": "esme@bibliotech.com",
                "password": PASSWORD,
            },
        )

        token = login.data["token"]

        try:
            self.probar_estado(
                "POST",
                "/api/auth/logout/",
                204,
                token=token,
                datos={},
            )

            self.probar_estado(
                "GET",
                "/api/auth/me/",
                401,
                token=token,
            )

        finally:
            # Si alguna verificación falla,
            # se vuelve a intentar revocar.
            try:
                llamar(
                    "POST",
                    "/api/auth/logout/",
                    token=token,
                    datos={},
                )
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
