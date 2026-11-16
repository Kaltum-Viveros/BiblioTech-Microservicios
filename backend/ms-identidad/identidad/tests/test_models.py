
import hashlib

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from identidad.models import Rol, TokenAcceso, Usuario


class IdentidadModelsTests(TestCase):

    PASSWORD = "ClaveSegura123!"

    @classmethod
    def setUpTestData(cls):
        cls.rol = Rol.objects.create(
            nombre="estudiante",
            limite_prestamos_activos=5
        )

        cls.usuario = Usuario(
            nombre="Usuario de prueba",
            email="usuario@test.local",
            rol=cls.rol
        )

        cls.usuario.set_password(cls.PASSWORD)
        cls.usuario.save()

    def crear_token(self, expira_en=None):
        token_plano = "token-de-prueba"

        token_hash = hashlib.sha256(
            token_plano.encode("utf-8")
        ).hexdigest()

        return TokenAcceso.objects.create(
            usuario=self.usuario,
            token_hash=token_hash,
            expira_en=(
                expira_en
                or timezone.now() + timedelta(hours=8)
            )
        )

    def test_rol_se_guarda_correctamente(self):
        rol = Rol.objects.get(
            rol_id=self.rol.rol_id
        )

        self.assertEqual(rol.nombre, "estudiante")
        self.assertEqual(rol.limite_prestamos_activos, 5)

    def test_nombre_de_rol_no_se_duplica(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Rol.objects.create(
                    nombre="estudiante",
                    limite_prestamos_activos=5
                )

    def test_password_se_guarda_como_hash(self):
        self.assertNotEqual(
            self.usuario.contrasena_hash,
            self.PASSWORD
        )

        self.assertTrue(
            self.usuario.check_password(self.PASSWORD)
        )

    def test_password_incorrecta(self):
        self.assertFalse(
            self.usuario.check_password("Incorrecta123!")
        )

    def test_email_de_usuario_es_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                otro = Usuario(
                    nombre="Otro usuario",
                    email="usuario@test.local",
                    rol=self.rol
                )

                otro.set_password("OtraClave123!")
                otro.save()

    def test_token_activo(self):
        token = self.crear_token()

        self.assertTrue(token.esta_activo)
        self.assertEqual(len(token.token_hash), 64)
        self.assertNotEqual(
            token.token_hash,
            "token-de-prueba"
        )

    def test_token_expirado(self):
        token = self.crear_token(
            expira_en=timezone.now() - timedelta(minutes=1)
        )

        self.assertFalse(token.esta_activo)

    def test_token_revocado(self):
        token = self.crear_token()

        token.revocado_en = timezone.now()
        token.save(update_fields=["revocado_en"])

        self.assertFalse(token.esta_activo)
