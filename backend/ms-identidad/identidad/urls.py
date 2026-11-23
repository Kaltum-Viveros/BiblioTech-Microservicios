
from django.urls import path

from identidad.presentation.auth_views import (
    AccesoBibliotecarioView,
    AccesoLectorView,
    LoginView,
    LogoutView,
    UsuarioActualView,
)

from identidad.presentation.usuarios_views import (
    RolesListView,
    UsuarioDetailView,
    UsuariosListCreateView,
)

from identidad.presentation.internal_views import (
    ResolverUsuariosInternoView,
    UsuarioInternoView,
    ValidarTokenInternoView,
)


urlpatterns = [
    # -----------------------------------------
    # API PÚBLICA — AUTENTICACIÓN (C04)
    # -----------------------------------------

    path(
        "auth/login/",
        LoginView.as_view(),
        name="auth-login"
    ),

    path(
        "auth/logout/",
        LogoutView.as_view(),
        name="auth-logout"
    ),

    path(
        "auth/me/",
        UsuarioActualView.as_view(),
        name="auth-me"
    ),

    path(
        "auth/access/bibliotecario/",
        AccesoBibliotecarioView.as_view(),
        name="auth-access-bibliotecario"
    ),

    path(
        "auth/access/lector/",
        AccesoLectorView.as_view(),
        name="auth-access-lector"
    ),

    # -----------------------------------------
    # API PÚBLICA — USUARIOS Y ROLES (C05)
    # -----------------------------------------

    path(
        "usuarios/",
        UsuariosListCreateView.as_view(),
        name="usuarios-list-create"
    ),

    path(
        "usuarios/<int:usuario_id>/",
        UsuarioDetailView.as_view(),
        name="usuarios-detail"
    ),

    path(
        "roles/",
        RolesListView.as_view(),
        name="roles-list"
    ),

    # -----------------------------------------
    # API INTERNA — CONTRATOS REST (C06)
    # -----------------------------------------

    path(
        "internal/auth/validar/",
        ValidarTokenInternoView.as_view(),
        name="internal-auth-validar"
    ),

    path(
        "internal/usuarios/resolver/",
        ResolverUsuariosInternoView.as_view(),
        name="internal-usuarios-resolver"
    ),

    path(
        "internal/usuarios/<int:usuario_id>/",
        UsuarioInternoView.as_view(),
        name="internal-usuarios-detail"
    ),
]
