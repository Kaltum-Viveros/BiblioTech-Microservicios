import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class CirculacionNoDisponibleError(Exception):
    """No es posible confirmar si el usuario tiene préstamos activos."""


class CirculacionPrestamosClient:
    """Consulta REST a Circulación. No comparte base de datos."""

    def __init__(self, base_url=None, api_key=None, timeout=3):
        self.base_url = (
            base_url if base_url is not None
            else os.environ.get("CIRCULACION_INTERNAL_URL", "")
        ).rstrip("/")
        self.api_key = (
            api_key if api_key is not None
            else os.environ.get("CIRCULACION_INTERNAL_API_KEY", "")
        )
        self.timeout = timeout

    def tiene_prestamos_activos(self, usuario_id):
        parsed = urlparse(self.base_url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or not self.api_key
        ):
            raise CirculacionNoDisponibleError(
                "La integración con Circulación no está configurada."
            )

        query = urlencode({"usuario_id": usuario_id})
        url = (
            f"{self.base_url}/internal/prestamos/activos/?{query}"
        )
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "X-Internal-Service-Key": self.api_key,
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise CirculacionNoDisponibleError(
                        "Circulación no respondió satisfactoriamente."
                    )
                raw = response.read(4097)
                if len(raw) > 4096:
                    raise CirculacionNoDisponibleError(
                        "Respuesta inválida de Circulación."
                    )
                payload = json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            raise CirculacionNoDisponibleError(
                "No se pudo consultar Circulación."
            ) from error

        if (
            not isinstance(payload, dict)
            or type(payload.get("tiene_prestamos_activos")) is not bool
        ):
            raise CirculacionNoDisponibleError(
                "El contrato de Circulación no es válido."
            )

        return payload["tiene_prestamos_activos"]