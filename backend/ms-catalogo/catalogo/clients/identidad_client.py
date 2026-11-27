"""Validación de tokens contra la API interna REST de Identidad.

Nunca accede a las tablas de tokens ni usuarios de otro servicio.
"""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.exceptions import APIException


class IdentidadNoDisponible(APIException):
    status_code = 503
    default_detail = "El servicio de Identidad no está disponible temporalmente."
    default_code = "identidad_no_disponible"


@dataclass(frozen=True)
class RolRemoto:
    rol_id: int
    nombre: str
    limite_prestamos_activos: int


@dataclass(frozen=True)
class UsuarioRemoto:
    usuario_id: int
    nombre: str
    email: str
    rol: RolRemoto

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


def _entero(valor, minimo=1):
    return type(valor) is int and valor >= minimo


def _usuario_remoto(datos):
    """La respuesta de un proveedor no confiable se valida antes de usarla."""
    if not isinstance(datos, dict) or not isinstance(datos.get("rol"), dict):
        raise IdentidadNoDisponible()

    rol = datos["rol"]
    if not (
        _entero(datos.get("usuario_id"))
        and isinstance(datos.get("nombre"), str)
        and isinstance(datos.get("email"), str)
        and _entero(rol.get("rol_id"))
        and isinstance(rol.get("nombre"), str)
        and _entero(rol.get("limite_prestamos_activos"), minimo=0)
    ):
        raise IdentidadNoDisponible()

    return UsuarioRemoto(
        usuario_id=datos["usuario_id"],
        nombre=datos["nombre"],
        email=datos["email"],
        rol=RolRemoto(
            rol_id=rol["rol_id"],
            nombre=rol["nombre"],
            limite_prestamos_activos=rol["limite_prestamos_activos"],
        ),
    )


class IdentidadClient:
    RUTA_VALIDACION = "/api/internal/auth/validar/"

    def validar_token(self, token: str):
        """Retorna UsuarioRemoto o None. Fallos de red/contrato se traducen a 503."""
        clave = getattr(settings, "IDENTIDAD_INTERNAL_API_KEY", "")
        base = getattr(settings, "IDENTIDAD_INTERNAL_BASE_URL", "")
        timeout = getattr(settings, "IDENTIDAD_HTTP_TIMEOUT_SECONDS", 3)

        if (
            not isinstance(clave, str)
            or len(clave) < 16
            or not isinstance(base, str)
            or not base.startswith("http://")
            or not isinstance(timeout, (int, float))
            or timeout <= 0
        ):
            raise IdentidadNoDisponible()

        solicitud = Request(
            base.rstrip("/") + self.RUTA_VALIDACION,
            data=json.dumps({"token": token}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Internal-Service-Key": clave,
            },
            method="POST",
        )

        try:
            with urlopen(solicitud, timeout=timeout) as respuesta:
                if respuesta.status != 200:
                    raise IdentidadNoDisponible()
                contenido = respuesta.read()
            datos = json.loads(contenido)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError):
            raise IdentidadNoDisponible() from None

        if not isinstance(datos, dict) or type(datos.get("valido")) is not bool:
            raise IdentidadNoDisponible()

        if datos["valido"] is False:
            return None

        if not isinstance(datos.get("expira_en"), str) or not datos["expira_en"]:
            raise IdentidadNoDisponible()

        return _usuario_remoto(datos.get("usuario"))
