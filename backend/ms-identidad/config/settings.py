"""Configuración inicial del microservicio de Identidad.

C01: solo healthchecks. El monolito sigue atendiendo el frontend.
"""

import os

from django.core.exceptions import ImproperlyConfigured


def lista_entorno(nombre: str, defecto: str) -> list[str]:
    return [
        x.strip()
        for x in os.getenv(nombre, defecto).split(",")
        if x.strip()
    ]


DEBUG = os.getenv("DJANGO_DEBUG", "0").lower() in (
    "1", "true", "yes"
)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = (
            "solo-desarrollo-identidad-no-usar-en-produccion"
        )
    else:
        raise ImproperlyConfigured(
            "Configura DJANGO_SECRET_KEY para Identidad."
        )


ALLOWED_HOSTS = lista_entorno(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,identidad"
)

CORS_ALLOWED_ORIGINS = lista_entorno(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:4200"
)


INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "identidad",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]


ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# Base de datos propia de Identidad.
# Se aprovisionará en el commit 02.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",

        "NAME": os.getenv(
            "IDENTIDAD_DB_NAME",
            "db_identidad"
        ),

        "USER": os.getenv(
            "IDENTIDAD_DB_USER",
            "identidad_app"
        ),

        "PASSWORD": os.getenv(
            "IDENTIDAD_DB_PASSWORD",
            ""
        ),

        "HOST": os.getenv(
            "IDENTIDAD_DB_HOST",
            "db"
        ),

        "PORT": os.getenv(
            "IDENTIDAD_DB_PORT",
            "3306"
        ),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = os.getenv(
    "DJANGO_TIME_ZONE",
    "America/Mexico_City"
)

USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_TOKEN_TTL_HOURS = int(
    os.getenv("AUTH_TOKEN_TTL_HOURS", "8")
)


# La autenticación Bearer existente se
# trasladará después de migrar los modelos.
# Por ahora no existen endpoints de negocio.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated"
    ],
}