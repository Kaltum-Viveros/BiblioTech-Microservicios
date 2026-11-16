
import hashlib
import os

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from identidad.models import Rol, TokenAcceso, Usuario


class SeedIdentidadTests(TestCase):

    PASSWORD = "ClaveDemo12345!"

    def ejecutar_seed(self, *args):
        with patch.dict(
            os.environ,
            {"IDENTIDAD_SEED_PASSWORD": self.PASSWORD}
        ):
            call_command(
                "seed_identidad_demo",
                *args,
                stdout=StringIO()
            )

    def test_seed_crea_roles_y_usuarios(self):
        self.ejecutar_seed()

        self.assertEqual(Rol.objects.count(), 3)
        self.assertEqual(Usuario.objects.count(), 3)

        rol = Rol.objects.get(nombre="estudiante")

        usuario = Usuario.objects.get(
            email="esme@bibliotech.com"
        )

        self.assertEqual(usuario.rol, rol)
        self.assertTrue(
            usuario.check_password(self.PASSWORD)
        )

    def test_seed_es_idempotente(self):
        self.ejecutar_seed()
        self.ejecutar_seed()

        self.assertEqual(Rol.objects.count(), 3)
        self.assertEqual(Usuario.objects.count(), 3)

    def test_seed_no_sobrescribe_password_existente(self):
        self.ejecutar_seed()

        usuario = Usuario.objects.get(
            email="esme@bibliotech.com"
        )

        usuario.set_password("ClavePersonal2026!")
        usuario.save(update_fields=["contrasena_hash"])

        self.ejecutar_seed()

        usuario.refresh_from_db()

        self.assertTrue(
            usuario.check_password("ClavePersonal2026!")
        )

        self.assertFalse(
            usuario.check_password(self.PASSWORD)
        )

    def test_reset_passwords_revoca_tokens(self):
        self.ejecutar_seed()

        usuario = Usuario.objects.get(
            email="esme@bibliotech.com"
        )

        usuario.set_password("ClaveAnterior123!")
        usuario.save(update_fields=["contrasena_hash"])

        token = TokenAcceso.objects.create(
            usuario=usuario,
            token_hash=hashlib.sha256(
                b"token-de-prueba-reset"
            ).hexdigest(),
            expira_en=timezone.now() + timedelta(hours=8)
        )

        self.ejecutar_seed("--reset-passwords")

        usuario.refresh_from_db()
        token.refresh_from_db()

        self.assertTrue(
            usuario.check_password(self.PASSWORD)
        )

        self.assertIsNotNone(token.revocado_en)
        self.assertFalse(token.esta_activo)

    def test_seed_requiere_password(self):
        with patch.dict(
            os.environ,
            {"IDENTIDAD_SEED_PASSWORD": ""}
        ):
            with self.assertRaises(CommandError):
                call_command(
                    "seed_identidad_demo",
                    stdout=StringIO()
                )
