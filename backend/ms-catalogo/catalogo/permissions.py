"""Permisos basados en el rol que validó Identidad, sin modelos locales."""

from rest_framework.permissions import BasePermission


class RolPermission(BasePermission):
    roles_permitidos = frozenset()

    def has_permission(self, request, view):
        usuario = request.user
        if not getattr(usuario, "is_authenticated", False):
            return False

        rol = getattr(usuario, "rol", None)
        nombre = getattr(rol, "nombre", None)
        return (
            isinstance(nombre, str)
            and nombre.strip().casefold() in self.roles_permitidos
        )


class IsBibliotecario(RolPermission):
    roles_permitidos = frozenset({"bibliotecario"})
    message = "Esta operación requiere el rol de bibliotecario."


class PuedeConsultarCatalogo(RolPermission):
    roles_permitidos = frozenset({"estudiante", "docente", "bibliotecario"})
    message = "Esta operación requiere un rol autorizado para consultar el catálogo."
