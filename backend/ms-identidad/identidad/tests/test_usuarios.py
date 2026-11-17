from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from identidad.clients.circulacion_client import CirculacionNoDisponibleError
from identidad.models import Rol, Usuario


class UsuariosApiTests(APITestCase):
    PASSWORD = "Biblioteca123*"

    @classmethod
    def setUpTestData(cls):
        cls.roles = {
            nombre: Rol.objects.create(
                nombre=nombre,
                limite_prestamos_activos=limite
            )
            for nombre, limite in (
                ("estudiante", 5),
                ("docente", 5),
                ("bibliotecario", 0),
            )
        }
        cls.bibliotecario = cls.crear_usuario(
            "Bibliotecario", "biblio@test.local", "bibliotecario"
        )
        cls.estudiante = cls.crear_usuario(
            "Estudiante", "estudiante@test.local", "estudiante"
        )
        cls.docente = cls.crear_usuario(
            "Docente", "docente@test.local", "docente"
        )

    @classmethod
    def crear_usuario(cls, nombre, email, rol):
        usuario = Usuario(
            nombre=nombre,
            email=email,
            rol=cls.roles[rol],
        )
        usuario.set_password(cls.PASSWORD)
        usuario.save()
        return usuario

    def autenticar(self, email="biblio@test.local"):
        respuesta = self.client.post(
            reverse("auth-login"),
            {"email": email, "password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        token = respuesta.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def datos_registro(self, **cambios):
        datos = {
            "nombre": "Ana Martínez",
            "email": "ana@test.local",
            "direccion": "Puebla",
            "telefono": "2221234567",
            "rol_id": self.roles["estudiante"].rol_id,
            "password": "ClaveSegura123!",
        }
        datos.update(cambios)
        return datos

    def url_detalle(self, usuario):
        return reverse("usuarios-detail", kwargs={"usuario_id": usuario.usuario_id})

    def test_bibliotecario_registra_usuario(self):
        self.autenticar()
        respuesta = self.client.post(
            reverse("usuarios-list-create"), self.datos_registro(), format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(email="ana@test.local")
        self.assertTrue(usuario.check_password("ClaveSegura123!"))
        self.assertNotIn("password", respuesta.data)
        self.assertNotIn("contrasena_hash", respuesta.data)
        self.assertEqual(respuesta.data["rol"]["nombre"], "estudiante")

    def test_registro_bibliotecario_nuevo_no_depende_de_circulacion(self):
        self.autenticar()
        respuesta = self.client.post(
            reverse("usuarios-list-create"),
            self.datos_registro(rol_id=self.roles["bibliotecario"].rol_id),
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data["rol"]["nombre"], "bibliotecario")

    def test_listar_usuarios_paginados(self):
        self.autenticar()
        respuesta = self.client.get(
            reverse("usuarios-list-create"), {"page": 1, "page_size": 2}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 3)
        self.assertEqual(len(respuesta.data["results"]), 2)
        self.assertIsNotNone(respuesta.data["next"])
        self.assertIsNone(respuesta.data["previous"])

    def test_consultar_usuario(self):
        self.autenticar()
        respuesta = self.client.get(self.url_detalle(self.estudiante))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["email"], self.estudiante.email)
        self.assertEqual(
            set(respuesta.data),
            {"usuario_id", "nombre", "email", "direccion", "telefono", "rol"},
        )

    def test_actualizar_telefono(self):
        self.autenticar()
        respuesta = self.client.patch(
            self.url_detalle(self.estudiante),
            {"telefono": "2229876543"}, format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.telefono, "2229876543")

    def test_cambiar_estudiante_a_docente_sin_circulacion(self):
        self.autenticar()
        respuesta = self.client.patch(
            self.url_detalle(self.estudiante),
            {"rol_id": self.roles["docente"].rol_id}, format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.rol_id, self.roles["docente"].rol_id)

    def test_correo_duplicado(self):
        self.autenticar()
        respuesta = self.client.post(
            reverse("usuarios-list-create"),
            self.datos_registro(email=self.estudiante.email), format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("email", respuesta.data)

    def test_correo_duplicado_sin_importar_mayusculas(self):
        self.autenticar()
        respuesta = self.client.post(
            reverse("usuarios-list-create"),
            self.datos_registro(email="ESTUDIANTE@TEST.LOCAL"), format="json",
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_correo_invalido(self):
        self.autenticar()
        respuesta = self.client.post(
            reverse("usuarios-list-create"),
            self.datos_registro(email="correo-sin-formato"), format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("email", respuesta.data)

    def test_rol_inexistente(self):
        self.autenticar()
        respuesta = self.client.post(
            reverse("usuarios-list-create"),
            self.datos_registro(rol_id=999999), format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("rol_id", respuesta.data)

    def test_rol_no_permitido(self):
        self.autenticar()
        otro = Rol.objects.create(nombre="administrador", limite_prestamos_activos=0)
        respuesta = self.client.post(
            reverse("usuarios-list-create"),
            self.datos_registro(rol_id=otro.rol_id), format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(Usuario.objects.filter(email="ana@test.local").exists())

    def test_password_insegura(self):
        self.autenticar()
        respuesta = self.client.post(
            reverse("usuarios-list-create"),
            self.datos_registro(password="123"), format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("password", respuesta.data)

    def test_no_permite_modificar_password(self):
        self.autenticar()
        respuesta = self.client.patch(
            self.url_detalle(self.estudiante),
            {"password": "OtraClave123!"}, format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("password", respuesta.data)

    def test_no_permite_hash_inyectado(self):
        self.autenticar()
        respuesta = self.client.patch(
            self.url_detalle(self.estudiante),
            {"contrasena_hash": "hash-falso"}, format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("contrasena_hash", respuesta.data)

    def test_usuario_no_encontrado(self):
        self.autenticar()
        respuesta = self.client.get(
            reverse("usuarios-detail", kwargs={"usuario_id": 999999})
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_sin_autenticacion(self):
        respuesta = self.client.get(reverse("usuarios-list-create"))
        self.assertEqual(respuesta.status_code, 401)

    def test_estudiante_no_administra_usuarios(self):
        self.autenticar("estudiante@test.local")
        respuesta = self.client.get(reverse("usuarios-list-create"))
        self.assertEqual(respuesta.status_code, 403)

    def test_docente_no_registra_usuarios(self):
        self.autenticar("docente@test.local")
        respuesta = self.client.post(
            reverse("usuarios-list-create"), self.datos_registro(), format="json"
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_solo_lista_roles_permitidos(self):
        self.autenticar()
        Rol.objects.create(nombre="administrador", limite_prestamos_activos=0)
        respuesta = self.client.get(reverse("roles-list"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            {rol["nombre"] for rol in respuesta.data},
            {"estudiante", "docente", "bibliotecario"},
        )

    def test_roles_requiere_bibliotecario(self):
        self.autenticar("estudiante@test.local")
        respuesta = self.client.get(reverse("roles-list"))
        self.assertEqual(respuesta.status_code, 403)

    def test_no_consultar_circulacion_si_rol_no_cambia(self):
        self.autenticar()
        with patch("identidad.services.usuarios_service.CirculacionPrestamosClient") as cliente:
            respuesta = self.client.patch(
                self.url_detalle(self.bibliotecario),
                {"rol_id": self.roles["bibliotecario"].rol_id}, format="json",
            )
            cliente.return_value.tiene_prestamos_activos.assert_not_called()
        self.assertEqual(respuesta.status_code, 200)

    def test_cambio_bibliotecario_falla_cerrado_sin_circulacion(self):
        self.autenticar()
        # No debe depender del entorno externo de ejecución del test.
        with patch("identidad.services.usuarios_service.CirculacionPrestamosClient") as cliente:
            cliente.return_value.tiene_prestamos_activos.side_effect = (
                CirculacionNoDisponibleError("Servicio ausente")
            )
            respuesta = self.client.patch(
                self.url_detalle(self.estudiante),
                {"nombre": "No debe cambiar", "rol_id": self.roles["bibliotecario"].rol_id},
                format="json",
            )
        self.assertEqual(respuesta.status_code, 503)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.rol_id, self.roles["estudiante"].rol_id)
        self.assertEqual(self.estudiante.nombre, "Estudiante")

    def test_cambio_bibliotecario_rechaza_prestamos_activos(self):
        self.autenticar()
        with patch("identidad.services.usuarios_service.CirculacionPrestamosClient") as cliente:
            cliente.return_value.tiene_prestamos_activos.return_value = True
            respuesta = self.client.patch(
                self.url_detalle(self.estudiante),
                {"rol_id": self.roles["bibliotecario"].rol_id}, format="json",
            )
            cliente.return_value.tiene_prestamos_activos.assert_called_once_with(
                self.estudiante.usuario_id
            )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("rol_id", respuesta.data)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.rol_id, self.roles["estudiante"].rol_id)

    def test_cambio_bibliotecario_permite_sin_prestamos_activos(self):
        self.autenticar()
        with patch("identidad.services.usuarios_service.CirculacionPrestamosClient") as cliente:
            cliente.return_value.tiene_prestamos_activos.return_value = False
            respuesta = self.client.patch(
                self.url_detalle(self.estudiante),
                {"rol_id": self.roles["bibliotecario"].rol_id}, format="json",
            )
        self.assertEqual(respuesta.status_code, 200)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.rol_id, self.roles["bibliotecario"].rol_id)