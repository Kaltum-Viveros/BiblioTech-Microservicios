#!/usr/bin/env python3
"""CATA08: enruta SOLO API pública de Catálogo en el gateway Nginx existente.

El archivo de Nginx es compartido por los microservicios. Este comando
valida colisiones y requiere --write para cambiarlo; nunca sobrescribe el
resto del archivo, ni su configuración de Identidad o Circulación.
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

ROUTES = ("libros", "autores", "categorias", "catalogo")
START = "# BEGIN CATA08: RUTAS PUBLICAS DE CATALOGO"
END = "# END CATA08: RUTAS PUBLICAS DE CATALOGO"


class ConfiguracionIncompatible(ValueError):
    """La configuración compartida requiere revisión humana."""


def _match_brace(source: str, index: int) -> int:
    """Localiza la llave de cierre, ignorando comentarios y comillas Nginx."""
    level = 0
    quote = None
    comment = False
    escaped = False
    for i in range(index, len(source)):
        char = source[i]
        if comment:
            if char == "\n":
                comment = False
            continue
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote:
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char == "#":
            comment = True
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            level += 1
        elif char == "}":
            level -= 1
            if level == 0:
                return i
    raise ConfiguracionIncompatible("Llaves de Nginx desbalanceadas.")


def _servers(source: str):
    """Devuelve solo bloques server reales (no menciones comentadas)."""
    for match in re.finditer(r"(?m)^\s*server\s*\{", source):
        prefix = source[source.rfind("\n", 0, match.start()) + 1:match.start()]
        if prefix.strip().startswith("#"):
            continue
        start = source.find("{", match.start(), match.end())
        yield start, _match_brace(source, start)


def _location_blocks(section: str):
    for m in re.finditer(r"(?m)^\s*location\s+([^\{\n]+?)\s*\{", section):
        begin = section.find("{", m.start(), m.end())
        yield m.group(1).strip(), section[begin + 1:_match_brace(section, begin)]


def _target_path(spec: str) -> str:
    # Solo se aceptan locations literales para evitar confundir expresiones regulares.
    parts = spec.split()
    if not parts:
        return ""
    if parts[0] in ("=", "^~") and len(parts) == 2:
        return parts[1]
    if len(parts) == 1 and parts[0].startswith("/"):
        return parts[0]
    return ""


def _public_locations() -> str:
    blocks = []
    for item in ROUTES:
        blocks.append(f"""    location = /api/{item} {{
        return 308 /api/{item}/$is_args$args;
    }}

    location ^~ /api/{item}/ {{
        proxy_pass http://ms-catalogo:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header X-Internal-Service-Key "";
    }}""")
    return ("\n    " + START + "\n\n" + "\n\n".join(blocks)
            + "\n\n    " + END + "\n")


def integrar(source: str) -> str:
    """Produce la nueva configuración o se niega antes de modificar el archivo."""
    if START in source or END in source:
        if source.count(START) == source.count(END) == 1:
            return source  # El bloque ya está instalado; idempotencia.
        raise ConfiguracionIncompatible("Marcadores CATA08 incompletos o duplicados.")

    servers = list(_servers(source))
    matches = []
    for opening, closing in servers:
        section = source[opening + 1:closing]
        if any("/api/" in spec for spec, _ in _location_blocks(section)):
            matches.append((opening, closing))
    if len(matches) != 1:
        raise ConfiguracionIncompatible(
            "Debe existir exactamente un bloque server que atienda /api/. "
            "No se modificó Nginx. Consulta con el responsable del gateway."
        )

    opening, closing = matches[0]
    section = source[opening + 1:closing]
    internal_guard = False
    for spec, content in _location_blocks(section):
        path = _target_path(spec)
        if any(path == f"/api/{name}" or path.startswith(f"/api/{name}/")
               for name in ROUTES):
            raise ConfiguracionIncompatible(
                f"La ruta {path} ya existe en Nginx. Revisa el gateway antes de continuar."
            )
        if path == "/api/internal/":
            if spec.startswith("="):
                raise ConfiguracionIncompatible(
                    "Un bloqueo exacto de /api/internal/ no protege sus subrutas."
                )
            if spec == "/api/internal/" and re.search(r"(?m)^\s*location\s+~", section):
                raise ConfiguracionIncompatible(
                    "La ruta /api/internal/ requiere ^~ si hay locations regex en Nginx."
                )
            if not re.search(r"\breturn\s+404\s*;", content):
                raise ConfiguracionIncompatible(
                    "Existe /api/internal/ pero no está protegido con return 404."
                )
            internal_guard = True

    if not internal_guard:
        # No instalamos un bloque nuevo de rutas internas sin conocer los contratos
        # del equipo de Identidad y las reglas compartidas del gateway.
        raise ConfiguracionIncompatible(
            "No se encontró 'location ... /api/internal/ { return 404; }'. "
            "Es necesario revisar el bloqueo de las API internas antes de enrutar Catálogo."
        )

    # Colocar al inicio del bloque server preserva todos los bloques existentes.
    return source[:opening + 1] + _public_locations() + source[opening + 1:]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path,
                        help="Ruta al archivo infra/nginx/default.conf montado en el contenedor")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--diff", action="store_true", help="Mostrar cambios sin escribir (predeterminado)")
    group.add_argument("--write", action="store_true", help="Aplicar los cambios después de revisarlos")
    args = parser.parse_args(argv)

    try:
        if not args.config.is_file():
            raise ConfiguracionIncompatible(f"No existe {args.config}.")
        before = args.config.read_text(encoding="utf-8")
        after = integrar(before)
        if before == after:
            print("CATA08: la configuración ya contiene las rutas; sin cambios.")
            return 0
        if args.write:
            args.config.write_text(after, encoding="utf-8", newline="")
            print(f"CATA08: se actualizaron las rutas públicas en {args.config}.")
            print("Comprueba 'git diff', 'nginx -t' y las rutas antes del commit.")
        else:
            diff = difflib.unified_diff(before.splitlines(keepends=True),
                                        after.splitlines(keepends=True),
                                        fromfile=str(args.config),
                                        tofile=str(args.config) + " (propuesta)")
            sys.stdout.writelines(diff)
            print("\nCATA08: vista previa; NO se modificó el archivo.")
        return 0
    except (OSError, UnicodeError, ConfiguracionIncompatible) as exc:
        print(f"CATA08: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
