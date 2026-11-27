"""Importa fixtures Django del monolito sin reasignar IDs bibliográficos.

Formato de entrada: salida de `manage.py dumpdata` con solo los cinco
modelos bibliográficos de `biblioteca`. La importación es atómica,
repetible y rechaza conflictos o modelos ajenos a Catálogo.
"""

import json
from datetime import date
from pathlib import Path
import sys

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from catalogo.models import Autor, Categoria, CategoriaLibro, Libro, LibroAutor


ESQUEMA = {
    "autor": (Autor, {"nombre"}, {"fecha_nacimiento", "nacionalidad"}, set()),
    "categoria": (Categoria, {"nombre_categoria"}, set(), set()),
    "libro": (Libro, {"titulo", "isbn"}, {"fecha_publicacion"}, set()),
    "libroautor": (LibroAutor, {"autor", "libro"}, set(), {"autor", "libro"}),
    "categorialibro": (
        CategoriaLibro, {"categoria", "libro"}, set(), {"categoria", "libro"}
    ),
}
ORDEN = ("autor", "categoria", "libro", "libroautor", "categorialibro")
FECHAS = {"fecha_nacimiento", "fecha_publicacion"}


def preparar_registros(registros):
    if not isinstance(registros, list) or not registros:
        raise CommandError("El archivo debe contener una lista JSON no vacía.")

    agrupados = {nombre: [] for nombre in ORDEN}
    vistos = set()
    for numero, registro in enumerate(registros, start=1):
        if not isinstance(registro, dict) or set(registro) != {"model", "pk", "fields"}:
            raise CommandError(f"Registro {numero}: estructura Django inválida.")
        etiqueta = registro["model"]
        if not isinstance(etiqueta, str) or "." not in etiqueta:
            raise CommandError(f"Registro {numero}: etiqueta de modelo inválida.")
        app, nombre = etiqueta.lower().split(".", 1)
        if app not in {"biblioteca", "catalogo"} or nombre not in ESQUEMA:
            raise CommandError(f"Registro {numero}: modelo no permitido: {etiqueta}.")
        pk, fields = registro["pk"], registro["fields"]
        if type(pk) is not int or pk <= 0 or not isinstance(fields, dict):
            raise CommandError(f"Registro {numero}: PK o campos inválidos.")
        if (nombre, pk) in vistos:
            raise CommandError(f"Registro {numero}: PK repetida {nombre}={pk}.")
        vistos.add((nombre, pk))

        _, obligatorios, opcionales, foraneas = ESQUEMA[nombre]
        if not obligatorios <= fields.keys() or fields.keys() - (obligatorios | opcionales):
            raise CommandError(f"Registro {numero}: campos faltantes o no permitidos.")

        normalizados = {}
        for campo in obligatorios | opcionales:
            valor = fields.get(campo)
            if campo in foraneas:
                if type(valor) is not int or valor <= 0:
                    raise CommandError(f"Registro {numero}: FK {campo} inválida.")
                normalizados[f"{campo}_id"] = valor
            elif campo in FECHAS and valor is not None:
                if not isinstance(valor, str):
                    raise CommandError(f"Registro {numero}: fecha {campo} inválida.")
                try:
                    normalizados[campo] = date.fromisoformat(valor)
                except ValueError as error:
                    raise CommandError(
                        f"Registro {numero}: fecha {campo} inválida."
                    ) from error
            else:
                normalizados[campo] = valor
        agrupados[nombre].append((pk, normalizados))
    return agrupados


class Command(BaseCommand):
    help = "Importa datos bibliográficos exportados desde el monolito conservando IDs."

    def add_arguments(self, parser):
        parser.add_argument(
            "archivo", help="Ruta del fixture JSON o - para leer desde stdin"
        )

        parser.add_argument(
            "--solo-validar",
            action="store_true",
            help="Verifica los datos y sus restricciones sin guardar registros",
        )

    def handle(self, *args, **options):
        nombre_archivo = options["archivo"]
        try:
            if nombre_archivo == "-":
                registros = json.load(sys.stdin)
            else:
                with open(Path(nombre_archivo), "r", encoding="utf-8") as archivo:
                    registros = json.load(archivo)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CommandError(f"No se pudo leer el fixture JSON: {error}") from error

        agrupados = preparar_registros(registros)
        creados = 0
        iguales = 0
        try:
            with transaction.atomic():
                for nombre in ORDEN:
                    modelo = ESQUEMA[nombre][0]
                    for pk, campos in agrupados[nombre]:
                        existente = modelo.objects.filter(pk=pk).first()
                        if existente is not None:
                            if any(getattr(existente, k) != v for k, v in campos.items()):
                                raise CommandError(
                                    f"Conflicto en {nombre} con ID {pk}. "
                                    "No se sobrescribió ningún dato."
                                )
                            iguales += 1
                            continue

                        instancia = modelo(pk=pk, **campos)
                        instancia.full_clean()
                        instancia.save(force_insert=True)
                        creados += 1
                if options["solo_validar"]:
                    transaction.set_rollback(True)
        except (ValidationError, IntegrityError) as error:
            raise CommandError(
                f"Importación cancelada por validación o integridad: {error}"
            ) from error

        if options["solo_validar"]:
            self.stdout.write(self.style.SUCCESS(
                f"Validación correcta: {creados} registros para crear y "
                f"{iguales} registros idénticos. No se guardaron registros."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Importación completada: {creados} registros creados y "
                f"{iguales} registros idénticos conservados."
            ))
