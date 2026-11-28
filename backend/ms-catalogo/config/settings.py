"""Configuración independiente del microservicio de Catálogo Bibliográfico.

CATA04: configuración del cliente de Identidad; aún sin API bibliográfica pública.
"""
import os
from django.core.exceptions import ImproperlyConfigured


def lista_entorno(nombre: str, defecto: str) -> list[str]:
    return [valor.strip() for valor in os.getenv(nombre, defecto).split(",") if valor.strip()]


DEBUG = os.getenv("DJANGO_DEBUG", "0").lower() in {"1", "true", "yes"}
SECRET_KEY = os.getenv("CATALOGO_DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Configura CATALOGO_DJANGO_SECRET_KEY.")

ALLOWED_HOSTS = lista_entorno(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,ms-catalogo"
)
CORS_ALLOWED_ORIGINS = lista_entorno(
    "CORS_ALLOWED_ORIGINS", "http://localhost:4200"
)

INSTALLED_APPS = [
    "django.contrib.auth",      # Dependencia técnica de Django/DRF, no almacena usuarios BiblioTech.
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "catalogo",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("CATALOGO_DB_NAME", ""),
        "USER": os.environ.get("CATALOGO_DB_USER", ""),
        "PASSWORD": os.environ.get("CATALOGO_DB_PASSWORD", ""),
        "HOST": os.environ.get("CATALOGO_DB_HOST", "db-catalogo"),
        "PORT": os.environ.get("CATALOGO_DB_PORT", "3306"),
    }
}
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "America/Mexico_City")
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Identidad valida el token del usuario. La clave nunca se expone al navegador.
IDENTIDAD_INTERNAL_BASE_URL = os.getenv(
    "IDENTIDAD_INTERNAL_BASE_URL", "http://ms-identidad:8000"
)
IDENTIDAD_INTERNAL_API_KEY = os.getenv("IDENTIDAD_INTERNAL_API_KEY", "")
IDENTIDAD_HTTP_TIMEOUT_SECONDS = float(
    os.getenv("IDENTIDAD_HTTP_TIMEOUT_SECONDS", "3")
)

# Autorización entre servicios: clave de Catálogo, distinta de la de Identidad.
CATALOGO_INTERNAL_API_KEY = os.getenv("CATALOGO_INTERNAL_API_KEY", "")

# Las rutas de negocio usarán IsAuthenticated y permisos específicos.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "catalogo.authentication.CatalogoTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
