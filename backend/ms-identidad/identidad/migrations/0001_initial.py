
import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [

        migrations.CreateModel(
            name="Rol",
            fields=[
                (
                    "rol_id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False
                    )
                ),
                (
                    "nombre",
                    models.CharField(
                        max_length=100,
                        unique=True
                    )
                ),
                (
                    "limite_prestamos_activos",
                    models.PositiveIntegerField()
                ),
            ],
        ),

        migrations.CreateModel(
            name="Usuario",
            fields=[
                (
                    "usuario_id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False
                    )
                ),
                (
                    "nombre",
                    models.CharField(max_length=100)
                ),
                (
                    "direccion",
                    models.CharField(
                        max_length=255,
                        null=True,
                        blank=True
                    )
                ),
                (
                    "telefono",
                    models.CharField(
                        max_length=15,
                        null=True,
                        blank=True
                    )
                ),
                (
                    "email",
                    models.EmailField(
                        max_length=50,
                        unique=True
                    )
                ),
                (
                    "contrasena_hash",
                    models.CharField(max_length=256)
                ),
                (
                    "rol",
                    models.ForeignKey(
                        db_column="rol_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="identidad.rol"
                    )
                ),
            ],
        ),

        migrations.CreateModel(
            name="TokenAcceso",
            fields=[
                (
                    "token_id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False
                    )
                ),
                (
                    "token_hash",
                    models.CharField(
                        max_length=64,
                        unique=True
                    )
                ),
                (
                    "creado_en",
                    models.DateTimeField(auto_now_add=True)
                ),
                (
                    "expira_en",
                    models.DateTimeField()
                ),
                (
                    "revocado_en",
                    models.DateTimeField(
                        null=True,
                        blank=True
                    )
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        db_column="usuario_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tokens_acceso",
                        to="identidad.usuario"
                    )
                ),
            ],

            options={
                "db_table": "identidad_tokens_acceso",

                "indexes": [
                    models.Index(
                        fields=["usuario", "revocado_en"],
                        name="identidad_tok_usr_rev_idx"
                    )
                ],
            },
        ),
    ]

import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [

        migrations.CreateModel(
            name="Rol",
            fields=[
                (
                    "rol_id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False
                    )
                ),
                (
                    "nombre",
                    models.CharField(
                        max_length=100,
                        unique=True
                    )
                ),
                (
                    "limite_prestamos_activos",
                    models.PositiveIntegerField()
                ),
            ],
        ),

        migrations.CreateModel(
            name="Usuario",
            fields=[
                (
                    "usuario_id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False
                    )
                ),
                (
                    "nombre",
                    models.CharField(max_length=100)
                ),
                (
                    "direccion",
                    models.CharField(
                        max_length=255,
                        null=True,
                        blank=True
                    )
                ),
                (
                    "telefono",
                    models.CharField(
                        max_length=15,
                        null=True,
                        blank=True
                    )
                ),
                (
                    "email",
                    models.EmailField(
                        max_length=50,
                        unique=True
                    )
                ),
                (
                    "contrasena_hash",
                    models.CharField(max_length=256)
                ),
                (
                    "rol",
                    models.ForeignKey(
                        db_column="rol_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="identidad.rol"
                    )
                ),
            ],
        ),

        migrations.CreateModel(
            name="TokenAcceso",
            fields=[
                (
                    "token_id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False
                    )
                ),
                (
                    "token_hash",
                    models.CharField(
                        max_length=64,
                        unique=True
                    )
                ),
                (
                    "creado_en",
                    models.DateTimeField(auto_now_add=True)
                ),
                (
                    "expira_en",
                    models.DateTimeField()
                ),
                (
                    "revocado_en",
                    models.DateTimeField(
                        null=True,
                        blank=True
                    )
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        db_column="usuario_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tokens_acceso",
                        to="identidad.usuario"
                    )
                ),
            ],

            options={
                "db_table": "identidad_tokens_acceso",

                "indexes": [
                    models.Index(
                        fields=["usuario", "revocado_en"],
                        name="identidad_tok_usr_rev_idx"
                    )
                ],
            },
        ),
    ]
