
from datetime import timedelta
from hashlib import sha256

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from identidad.models import Rol, TokenAcceso, Usuario


class AuthApiTests(APITestCase):

    PASSWORD = "Biblioteca123*"

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

        cls.rol_bibliotecario = Rol.objects.create(
            nombre="bibliotecario",
            limite_prestamos_activos=0
        )

        cls.estudiante = cls._crear_usuario(
            nombre="Estudiante Test",
            email="estudiante@test.local",
            rol=cls.rol_estudiante
        )

        cls.docente = cls._crear_usuario(
            nombre="Docente Test",
            email="docente@test.local",
            rol=cls.rol_docente
        )

        cls.bibliotecario = cls._crear_usuario(
            nombre="Bibliotecario Test",
            email="bibliotecario@test.local",
            rol=cls.rol_bibliotecario
        )

    @classmethod
    def _crear_usuario(cls, nombre, email, rol):
        usuario = Usuario(
            nombre=nombre,
            email=email,
            rol=rol
        )

        usuario.set_password(cls.PASSWORD)
        usuario.save()

        return usuario

    def _login(self, email, password=None):
        return self.client.post(
            reverse("auth-login"),
            {
                "email": email,
                "password": (
                    self.PASSWORD
                    if password is None
                    else password
                ),
            },
            format="json"
        )

    def _autenticar(self, email):
        response = self._login(email)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        token = response.data["token"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        return token

    def test_login_correcto(self):
        response = self._login(
            "estudiante@test.local"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertIn("token", response.data)
        self.assertIn("expira_en", response.data)

        self.assertEqual(
            response.data["tipo_token"],
            "Bearer"
        )

        self.assertEqual(
            response.data["usuario"]["rol"]["nombre"],
            "estudiante"
        )

    def test_login_normaliza_email(self):
        response = self._login(
            "  ESTUDIANTE@TEST.LOCAL  "
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_login_password_incorrecta(self):
        response = self._login(
            "estudiante@test.local",
            "Incorrecta123!"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

        self.assertEqual(
            response.data["detail"],
            "Credenciales incorrectas."
        )

    def test_login_usuario_inexistente(self):
        response = self._login(
            "noexiste@test.local"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_login_email_invalido(self):
        response = self._login(
            "correo-invalido"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_login_password_vacio(self):
        response = self._login(
            "estudiante@test.local",
            ""
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_login_no_expone_informacion_sensible(self):
        response = self._login(
            "estudiante@test.local"
        )

        usuario = response.data["usuario"]

        self.assertEqual(
            set(usuario.keys()),
            {"usuario_id", "nombre", "email", "rol"}
        )

        self.assertNotIn("password", usuario)
        self.assertNotIn("contrasena_hash", usuario)
        self.assertNotIn("token_hash", response.data)

    def test_token_se_guarda_hasheado(self):
        response = self._login(
            "estudiante@test.local"
        )

        token_plano = response.data["token"]

        hash_esperado = sha256(
            token_plano.encode("utf-8")
        ).hexdigest()

        token = TokenAcceso.objects.get(
            token_hash=hash_esperado
        )

        self.assertEqual(
            len(token.token_hash),
            64
        )

        self.assertNotEqual(
            token.token_hash,
            token_plano
        )

        self.assertTrue(token.esta_activo)

    @override_settings(AUTH_TOKEN_TTL_HOURS=2)
    def test_token_respeta_tiempo_de_expiracion(self):
        response = self._login(
            "estudiante@test.local"
        )

        token_hash = sha256(
            response.data["token"].encode("utf-8")
        ).hexdigest()

        token = TokenAcceso.objects.get(
            token_hash=token_hash
        )

        duracion = (
            token.expira_en - token.creado_en
        )

        self.assertGreaterEqual(
            duracion,
            timedelta(hours=2) - timedelta(seconds=5)
        )

        self.assertLessEqual(
            duracion,
            timedelta(hours=2) + timedelta(seconds=5)
        )

    def test_me_requiere_autenticacion(self):
        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

        self.assertEqual(
            response["WWW-Authenticate"],
            "Bearer"
        )

    def test_me_con_token_valido(self):
        self._autenticar(
            "estudiante@test.local"
        )

        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["email"],
            "estudiante@test.local"
        )

        self.assertEqual(
            response.data["rol"]["nombre"],
            "estudiante"
        )

    def test_me_token_invalido(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer token-inventado"
        )

        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_me_token_revocado(self):
        token_plano = self._autenticar(
            "estudiante@test.local"
        )

        token_hash = sha256(
            token_plano.encode("utf-8")
        ).hexdigest()

        TokenAcceso.objects.filter(
            token_hash=token_hash
        ).update(
            revocado_en=timezone.now()
        )

        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_me_token_expirado(self):
        token_plano = self._autenticar(
            "estudiante@test.local"
        )

        token_hash = sha256(
            token_plano.encode("utf-8")
        ).hexdigest()

        token = TokenAcceso.objects.get(
            token_hash=token_hash
        )

        token.expira_en = (
            timezone.now() - timedelta(minutes=1)
        )

        token.save(
            update_fields=["expira_en"]
        )

        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

        token.refresh_from_db()

        self.assertIsNotNone(
            token.revocado_en
        )

    def test_logout_invalida_el_token(self):
        self._autenticar(
            "estudiante@test.local"
        )

        response = self.client.post(
            reverse("auth-logout"),
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )

        response_me = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response_me.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_logout_requiere_token(self):
        response = self.client.post(
            reverse("auth-logout"),
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_sesiones_son_independientes(self):
        primera = self._login(
            "estudiante@test.local"
        )

        segunda = self._login(
            "estudiante@test.local"
        )

        token_1 = primera.data["token"]
        token_2 = segunda.data["token"]

        self.assertNotEqual(
            token_1,
            token_2
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_1}"
        )

        logout = self.client.post(
            reverse("auth-logout"),
            {},
            format="json"
        )

        self.assertEqual(
            logout.status_code,
            status.HTTP_204_NO_CONTENT
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_2}"
        )

        me = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            me.status_code,
            status.HTTP_200_OK
        )

    def test_estudiante_no_accede_como_bibliotecario(self):
        self._autenticar(
            "estudiante@test.local"
        )

        response = self.client.get(
            reverse("auth-access-bibliotecario")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_bibliotecario_tiene_acceso(self):
        self._autenticar(
            "bibliotecario@test.local"
        )

        response = self.client.get(
            reverse("auth-access-bibliotecario")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_docente_tiene_acceso_lector(self):
        self._autenticar(
            "docente@test.local"
        )

        response = self.client.get(
            reverse("auth-access-lector")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_estudiante_tiene_acceso_lector(self):
        self._autenticar(
            "estudiante@test.local"
        )

        response = self.client.get(
            reverse("auth-access-lector")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_bibliotecario_no_accede_como_lector(self):
        self._autenticar(
            "bibliotecario@test.local"
        )

        response = self.client.get(
            reverse("auth-access-lector")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_bearer_no_distingue_mayusculas(self):
        token = self._autenticar(
            "estudiante@test.local"
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"bEaReR {token}"
        )

        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_header_bearer_malformado(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer uno dos"
        )

        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_otro_esquema_no_autentica(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Basic abc123"
        )

        response = self.client.get(
            reverse("auth-me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )
