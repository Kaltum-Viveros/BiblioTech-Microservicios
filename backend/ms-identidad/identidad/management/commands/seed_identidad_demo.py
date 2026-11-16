
import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from identidad.models import Rol, TokenAcceso, Usuario


class Command(BaseCommand):

    help = (
        "Crea los roles y usuarios de demostración "
        "en la base de datos de Identidad."
    )

    ROLES = [
        ("estudiante", 5),
        ("docente", 5),
        ("bibliotecario", 0),
    ]

    USUARIOS = [
        {
            "nombre": "Esmeralda Urbina Cinto",
            "email": "esme@bibliotech.com",
            "rol": "estudiante",
        },
        {
            "nombre": "Josué Saúl Torres Zamora",
            "email": "saul@bibliotech.com",
            "rol": "docente",
        },
        {
            "nombre": "Kaltum Abdala Viveros Gómez",
            "email": "kalt@bibliotech.com",
            "rol": "bibliotecario",
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help=(
                "Restablece las contraseñas de usuarios demo "
                "existentes y revoca sus tokens."
            )
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("IDENTIDAD_SEED_PASSWORD")

        if not password or len(password) < 12:
            raise CommandError(
                "Configura IDENTIDAD_SEED_PASSWORD "
                "con al menos 12 caracteres."
            )

        roles = {}

        for nombre, limite in self.ROLES:
            rol, _ = Rol.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "limite_prestamos_activos": limite
                }
            )

            roles[nombre] = rol

        usuarios_creados = 0
        usuarios_restaurados = 0

        for datos in self.USUARIOS:
            usuario, creado = Usuario.objects.get_or_create(
                email=datos["email"],
                defaults={
                    "nombre": datos["nombre"],
                    "rol": roles[datos["rol"]],
                    "contrasena_hash": make_password(password),
                }
            )

            if creado:
                usuarios_creados += 1

            elif options["reset_passwords"]:
                usuario.nombre = datos["nombre"]
                usuario.rol = roles[datos["rol"]]
                usuario.set_password(password)

                usuario.save(
                    update_fields=[
                        "nombre",
                        "rol",
                        "contrasena_hash",
                    ]
                )

                TokenAcceso.objects.filter(
                    usuario=usuario,
                    revocado_en__isnull=True
                ).update(
                    revocado_en=timezone.now()
                )

                usuarios_restaurados += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed de Identidad ejecutado correctamente."
            )
        )

        self.stdout.write(
            f"Roles disponibles: {len(roles)}"
        )

        self.stdout.write(
            f"Usuarios creados: {usuarios_creados}"
        )

        self.stdout.write(
            f"Usuarios restablecidos: {usuarios_restaurados}"
        )

        self.stdout.write("")
        self.stdout.write("Cuentas de demostración:")

        for datos in self.USUARIOS:
            self.stdout.write(datos["email"])
