"""CATA05: copia las capas bibliográficas originales sin alterar el monolito.

Se ejecuta en Docker con backend/biblioteca montado en /fuentes:ro.
Antes de escribir verifica la presencia y sintaxis de todos los archivos.
"""

import argparse
import ast
import re
from pathlib import Path


MODULOS = {
    "repositories": ("libro_repository.py", "autor_repository.py", "categoria_repository.py"),
    "services": ("libro_service.py", "autor_service.py", "categoria_service.py"),
    "presentation": (
        "libros_serializers.py", "autores_serializers.py", "categorias_serializers.py",
        "libros_views.py", "autores_views.py", "categorias_views.py",
    ),
}


def quitar_nodos(texto, clase, metodos=(), clases=()):
    """Retira solo operaciones de eliminación no expuestas públicamente."""
    arbol = ast.parse(texto)
    rangos = []
    for nodo in arbol.body:
        if not isinstance(nodo, ast.ClassDef):
            continue
        if nodo.name in clases:
            rangos.append((nodo.lineno, nodo.end_lineno))
        elif nodo.name == clase:
            for metodo in nodo.body:
                if isinstance(metodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and metodo.name in metodos:
                    inicio = min((d.lineno for d in metodo.decorator_list), default=metodo.lineno)
                    rangos.append((inicio, metodo.end_lineno))
    lineas = texto.splitlines(keepends=True)
    for inicio, fin in sorted(rangos, reverse=True):
        del lineas[inicio-1:fin]
    return "".join(lineas)


def adaptar(seccion, nombre, contenido):
    contenido = contenido.replace("biblioteca.", "catalogo.")
    contenido = contenido.replace(
        "catalogo.presentation.usuarios_serializers",
        "catalogo.presentation.common_serializers",
    )

    if (seccion, nombre) == ("repositories", "libro_repository.py"):
        contenido = quitar_nodos(contenido, "ILibroRepository", {"tiene_ejemplares"})
        contenido = quitar_nodos(contenido, "DjangoLibroRepository", {"tiene_ejemplares"})
        # Ejemplar pertenece a Circulación y no debe importarse desde Catálogo.
        contenido = re.sub(
            r"(?m)^(from catalogo.models import .*?)\bEjemplar,?\s*",
            lambda m: m.group(1),
            contenido,
        )
        # La importación original es en una sola línea; mantener el formato.
        contenido = contenido.replace("CategoriaLibro,  Libro", "CategoriaLibro, Libro")
    if (seccion, nombre) == ("services", "libro_service.py"):
        contenido = quitar_nodos(
            contenido, "LibroService", {"eliminar_libro"}, {"LibroConEjemplaresError"}
        )

    arbol = ast.parse(contenido, filename=nombre)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            if nodo.module.startswith("biblioteca"):
                raise ValueError(f"Importación antigua no adaptada en {nombre}: {nodo.module}")
            if nodo.module == "catalogo.presentation.usuarios_serializers":
                raise ValueError(f"Serializador compartido no adaptado: {nombre}")
        if isinstance(nodo, ast.Name) and nodo.id in {"Ejemplar", "Prestamo", "Usuario", "Sancion"}:
            raise ValueError(f"Dependencia de otro servicio en {nombre}: {nodo.id}")
    return contenido


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origen", type=Path, required=True, help="Directorio original biblioteca/")
    args = parser.parse_args()
    raiz = Path(__file__).resolve().parents[1] / "catalogo"
    pendientes = {}

    for seccion, nombres in MODULOS.items():
        for nombre in nombres:
            fuente = args.origen / seccion / nombre
            destino = raiz / seccion / nombre
            if not fuente.is_file():
                raise SystemExit(f"Falta código fuente original: {fuente}")
            if destino.exists():
                raise SystemExit(f"El destino ya existe. No se sobrescribe: {destino}")
            pendientes[destino] = adaptar(seccion, nombre, fuente.read_text(encoding="utf-8"))

    # Preparación completa antes de crear archivos; el monolito nunca se modifica.
    for destino in pendientes:
        destino.parent.mkdir(parents=True, exist_ok=True)
        init = destino.parent / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")
    for destino, contenido in pendientes.items():
        destino.write_text(contenido, encoding="utf-8")
    print(f"CATA05: {len(pendientes)} módulos bibliográficos copiados y adaptados.")
    print("Sin cambios en backend/biblioteca/. Ejecuta check y pruebas antes del commit.")


if __name__ == "__main__":
    main()
