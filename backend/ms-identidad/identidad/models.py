
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class Rol(models.Model):
    rol_id = models.AutoField(primary_key=True)

    nombre = models.CharField(
        max_length=100,
        unique=True
    )

    limite_prestamos_activos = models.PositiveIntegerField()

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    usuario_id = models.AutoField(primary_key=True)

    rol = models.ForeignKey(
        Rol,
        on_delete=models.CASCADE,
        db_column="rol_id"
    )

    nombre = models.CharField(max_length=100)

    direccion = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    telefono = models.CharField(
        max_length=15,
        null=True,
        blank=True
    )

    email = models.EmailField(
        max_length=50,
        unique=True
    )

    contrasena_hash = models.CharField(max_length=256)

    def set_password(self, raw_password):
        self.contrasena_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(
            raw_password,
            self.contrasena_hash
        )

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return self.nombre


class TokenAcceso(models.Model):
    token_id = models.AutoField(primary_key=True)

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column="usuario_id",
        related_name="tokens_acceso"
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    expira_en = models.DateTimeField()

    revocado_en = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = "identidad_tokens_acceso"

        indexes = [
            models.Index(
                fields=["usuario", "revocado_en"],
                name="identidad_tok_usr_rev_idx"
            )
        ]

    @property
    def esta_activo(self):
        return (
            self.revocado_en is None
            and self.expira_en > timezone.now()
        )

    def __str__(self):
        return f"Token de {self.usuario.email}"
