"""Consulta de existencias a Circulación por REST interno, nunca por SQL.

Contrato propuesto para el equipo de Circulación; falla explícitamente cuando
la dependencia no está lista o devuelve datos ambiguos/incompletos.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.exceptions import APIException


class CirculacionNoDisponible(APIException):
    status_code = 503
    default_detail = "Las existencias no están disponibles temporalmente."
    default_code = "circulacion_no_disponible"


class CirculacionClient:
    RUTA_EXISTENCIAS = "/api/internal/existencias/consultar/"
    MAX_LIBROS_POR_LOTE = 100

    def consultar_existencias(self, libros_ids):
        """Dict {libro_id: {stock_total, stock_disponible}}; exige cobertura total.

        Devuelve {} cuando no hay libros. Nunca convierte errores en stock cero.
        """
        ids = list(dict.fromkeys(libros_ids))
        if any(type(pk) is not int or pk <= 0 for pk in ids):
            raise ValueError("Todos los libros_ids deben ser enteros positivos.")
        if not ids:
            return {}

        resultado = {}
        for inicio in range(0, len(ids), self.MAX_LIBROS_POR_LOTE):
            lote = ids[inicio:inicio + self.MAX_LIBROS_POR_LOTE]
            resultado.update(self._consultar_lote(lote))
        return resultado

    def _consultar_lote(self, ids):
        base = getattr(settings, "CIRCULACION_INTERNAL_BASE_URL", "")
        clave = getattr(settings, "CIRCULACION_INTERNAL_API_KEY", "")
        timeout = getattr(settings, "CIRCULACION_HTTP_TIMEOUT_SECONDS", 3)
        if not (
            isinstance(base, str)
            and base.startswith(("http://", "https://"))
            and isinstance(clave, str)
            and len(clave) >= 16
            and type(timeout) in (float, int)
            and timeout > 0
        ):
            raise CirculacionNoDisponible()

        solicitud = Request(
            base.rstrip("/") + self.RUTA_EXISTENCIAS,
            data=json.dumps({"libros_ids": ids}).encode("utf-8"),
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
                    raise CirculacionNoDisponible()
                # Limitar el volumen de una respuesta interna inesperada.
                contenido = respuesta.read(1024 * 1024 + 1)
                if len(contenido) > 1024 * 1024:
                    raise CirculacionNoDisponible()
            datos = json.loads(contenido)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError):
            raise CirculacionNoDisponible() from None

        if not isinstance(datos, dict) or not isinstance(datos.get("existencias"), list):
            raise CirculacionNoDisponible()

        resultado = {}
        ids_solicitados = set(ids)
        for entrada in datos["existencias"]:
            if not isinstance(entrada, dict):
                raise CirculacionNoDisponible()
            libro_id = entrada.get("libro_id")
            total = entrada.get("stock_total")
            disponible = entrada.get("stock_disponible")
            if not (
                type(libro_id) is int
                and libro_id in ids_solicitados
                and libro_id not in resultado
                and type(total) is int
                and type(disponible) is int
                and 0 <= disponible <= total
            ):
                raise CirculacionNoDisponible()
            resultado[libro_id] = {
                "stock_total": total,
                "stock_disponible": disponible,
            }

        # Un libro sin ejemplares debe declararse explícitamente con ceros.
        # Omisiones no se interpretan como 0.
        if set(resultado) != ids_solicitados:
            raise CirculacionNoDisponible()
        return resultado
