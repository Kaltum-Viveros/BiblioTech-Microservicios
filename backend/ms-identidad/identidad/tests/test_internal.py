
from datetime import timedelta
from hashlib import sha256

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from identidad.models import Rol, TokenAcceso, Usuario


TEST_INTERNAL_KEY = (
    "clave-interna-exclusiva-para-pruebas-0123456789ABCDEF"
)


@override_settings(
    IDENTIDAD_INTERNAL_API_KEY=TEST_INTERNAL_KEY
)
class InternalContratoApiTests(APITestCase):

    TOKEN_PLANO = "token-interno-de-prueba-2026"

    @classmethod
    def setUpTestData(cls):
        cls.rol_estudiante = Rol.objects.create(
            nombre="estudiante",
            limite_prestamos_activos=5
        )

        cls.rol_docente = Rol.objects.create(
            nombre="docente",
            limite_prestamos_activos=5
        )

        cls.estudiante = Usuario(
            nombre="Estudiante Interno",
            email="estudiante.interno@test.local",
            rol=cls.rol_estudiante
        )

        cls.estudiante.set_password(
            "ClaveSegura123!"
        )

        cls.estudiante.save()

        cls.docente = Usuario(
            nombre="Docente Interno",
            email="docente.interno@test.local",
            rol=cls.rol_docente
        )

        cls.docente.set_password(
            "ClaveSegura456!"
        )

        cls.docente.save()

        cls.token = TokenAcceso.objects.create(
            usuario=cls.estudiante,
            token_hash=sha256(
                cls.TOKEN_PLANO.encode("utf-8")
            ).hexdigest(),
            expira_en=(
                timezone.now()
                + timedelta(hours=8)
            )
        )

    def setUp(self):
        self.client.credentials(
            HTTP_X_INTERNAL_SERVICE_KEY=TEST_INTERNAL_KEY
        )

    def url_validar(self):
        return reverse(
            "internal-auth-validar"
        )

    def url_usuario(self, usuario_id):
        return reverse(
            "internal-usuarios-detail",
            kwargs={
                "usuario_id": usuario_id
            }
        )

    def url_resolver(self):
        return reverse(
            "internal-usuarios-resolver"
        )

    def validar(self, token_plano=None):
        return self.client.post(
            self.url_validar(),
            {
                "token": (
                    self.TOKEN_PLANO
                    if token_plano is None
                    else token_plano
                )
            },
            format="json"
        )

    # =========================================
    # 01. VALIDACION DE TOKEN VIGENTE
    # =========================================

    def test_valida_token_vigente(self):
        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )

        self.assertTrue(
            respuesta.data["valido"]
        )

        self.assertEqual(
            respuesta.data["usuario"]["usuario_id"],
            self.estudiante.usuario_id
        )

        self.assertEqual(
            respuesta.data["usuario"]["rol"]["nombre"],
            "estudiante"
        )

        self.assertIsNotNone(
            respuesta.data["expira_en"]
        )

    # =========================================
    # 02. INFORMACION SENSIBLE
    # =========================================

    def test_validacion_no_expone_datos_sensibles(self):
        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )

        usuario = respuesta.data["usuario"]

        self.assertEqual(
            set(usuario.keys()),
            {
                "usuario_id",
                "nombre",
                "email",
                "rol"
            }
        )

        self.assertNotIn(
            "contrasena_hash",
            usuario
        )

        self.assertNotIn(
            "token_hash",
            respuesta.data
        )

        self.assertNotIn(
            "direccion",
            usuario
        )

        self.assertNotIn(
            "telefono",
            usuario
        )

    # =========================================
    # 03. TOKEN INEXISTENTE
    # =========================================

    def test_token_inexistente_devuelve_valido_false(self):
        respuesta = self.validar(
            "token-que-no-existe"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )

        self.assertFalse(
            respuesta.data["valido"]
        )

        self.assertIsNone(
            respuesta.data["usuario"]
        )

        self.assertIsNone(
            respuesta.data["expira_en"]
        )

    # =========================================
    # 04. TOKEN REVOCADO
    # =========================================

    def test_token_revocado_devuelve_valido_false(self):
        TokenAcceso.objects.filter(
            token_id=self.token.token_id
        ).update(
            revocado_en=timezone.now()
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )

        self.assertFalse(
            respuesta.data["valido"]
        )

    # =========================================
    # 05. TOKEN EXPIRADO
    # =========================================

    def test_token_expirado_se_revoca(self):
        TokenAcceso.objects.filter(
            token_id=self.token.token_id
        ).update(
            expira_en=(
                timezone.now()
                - timedelta(minutes=1)
            )
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )

        self.assertFalse(
            respuesta.data["valido"]
        )

        token = TokenAcceso.objects.get(
            token_id=self.token.token_id
        )

        self.assertIsNotNone(
            token.revocado_en
        )

    # =========================================
    # 06. TOKEN OBLIGATORIO
    # =========================================

    def test_validacion_requiere_token(self):
        respuesta = self.client.post(
            self.url_validar(),
            {},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertIn(
            "token",
            respuesta.data
        )

    # =========================================
    # 07. TOKEN DEMASIADO LARGO
    # =========================================

    def test_validacion_rechaza_token_demasiado_largo(self):
        respuesta = self.validar(
            "A" * 513
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertIn(
            "token",
            respuesta.data
        )

    # =========================================
    # 08. SIN CLAVE INTERNA
    # =========================================

    def test_sin_clave_interna_devuelve_403(self):
        self.client.credentials()

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    # =========================================
    # 09. CLAVE INTERNA INCORRECTA
    # =========================================

    def test_clave_interna_incorrecta_devuelve_403(self):
        self.client.credentials(
            HTTP_X_INTERNAL_SERVICE_KEY="clave-incorrecta"
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    # =========================================
    # 10. BEARER NO SUSTITUYE CLAVE INTERNA
    # =========================================

    def test_bearer_no_reemplaza_clave_interna(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {self.TOKEN_PLANO}"
            )
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    # =========================================
    # 11. SIN CONFIGURACION DE CLAVE
    # =========================================

    @override_settings(
        IDENTIDAD_INTERNAL_API_KEY=""
    )
    def test_sin_configuracion_se_deniega_acceso(self):
        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    # =========================================
    # 12. CLAVE DEMASIADO CORTA
    # NUEVA PRUEBA PARA COMPLETAR LAS 86
    # =========================================

    @override_settings(
        IDENTIDAD_INTERNAL_API_KEY="insegura"
    )
    def test_clave_configurada_demasiado_corta_se_rechaza(self):
        # La clave recibida coincide exactamente
        # con la configurada, pero tiene menos
        # de los 16 caracteres requeridos.

        self.client.credentials(
            HTTP_X_INTERNAL_SERVICE_KEY="insegura"
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    # =========================================
    # 13. CONSULTAR USUARIO EXISTENTE
    # =========================================

    def test_consultar_usuario_existente(self):
        respuesta = self.client.get(
            self.url_usuario(
                self.docente.usuario_id
            )
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            respuesta.data["email"],
            "docente.interno@test.local"
        )

        self.assertEqual(
            respuesta.data["rol"]["nombre"],
            "docente"
        )

    # =========================================
    # 14. USUARIO INEXISTENTE
    # =========================================

    def test_usuario_inexistente_devuelve_404(self):
        respuesta = self.client.get(
            self.url_usuario(999999)
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_404_NOT_FOUND
        )

        self.assertEqual(
            respuesta.data["detail"],
            "Usuario no encontrado."
        )

    # =========================================
    # 15. CONSULTA SIN CLAVE INTERNA
    # =========================================

    def test_consulta_usuario_requiere_clave(self):
        self.client.credentials()

        respuesta = self.client.get(
            self.url_usuario(
                self.estudiante.usuario_id
            )
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    # =========================================
    # 16. RESOLVER VARIOS USUARIOS
    # =========================================

    def test_resolver_varios_usuarios(self):
        respuesta = self.client.post(
            self.url_resolver(),
            {
                "usuarios_ids": [
                    self.docente.usuario_id,
                    self.estudiante.usuario_id,
                    self.docente.usuario_id,
                    999999
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )

        ids = [
            usuario["usuario_id"]
            for usuario in respuesta.data["usuarios"]
        ]

        self.assertEqual(
            ids,
            [
                self.docente.usuario_id,
                self.estudiante.usuario_id
            ]
        )

        self.assertEqual(
            respuesta.data["no_encontrados"],
            [999999]
        )

    # =========================================
    # 17. LISTA VACIA DE IDENTIFICADORES
    # =========================================

    def test_resolver_identificadores_vacios_devuelve_400(self):
        respuesta = self.client.post(
            self.url_resolver(),
            {
                "usuarios_ids": []
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertIn(
            "usuarios_ids",
            respuesta.data
        )

    # =========================================
    # 18. MAS DE 100 IDENTIFICADORES
    # =========================================

    def test_resolver_rechaza_mas_de_100_identificadores(self):
        respuesta = self.client.post(
            self.url_resolver(),
            {
                "usuarios_ids": list(
                    range(1, 102)
                )
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    # =========================================
    # 19. IDENTIFICADORES INVALIDOS
    # =========================================

    def test_resolver_rechaza_identificadores_invalidos(self):
        respuesta = self.client.post(
            self.url_resolver(),
            {
                "usuarios_ids": [
                    "no-es-un-id"
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    # =========================================
    # 20. RESOLVER USUARIOS SIN CLAVE
    # =========================================

    def test_resolver_requiere_clave_interna(self):
        self.client.credentials()

        respuesta = self.client.post(
            self.url_resolver(),
            {
                "usuarios_ids": [
                    self.estudiante.usuario_id
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    # =========================================
    # 21. METODO HTTP NO PERMITIDO
    # =========================================

    def test_validar_token_no_admite_get(self):
        respuesta = self.client.get(
            self.url_validar()
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
