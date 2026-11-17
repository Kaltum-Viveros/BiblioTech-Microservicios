from abc import ABC, abstractmethod

from identidad.models import Rol, Usuario


class IUsuarioRepository(ABC):
    @abstractmethod
    def listar(self):
        pass

    @abstractmethod
    def obtener_por_id(self, usuario_id):
        pass

    @abstractmethod
    def obtener_por_email(self, email):
        pass

    @abstractmethod
    def crear(self, usuario):
        pass

    @abstractmethod
    def actualizar(self, usuario, campos):
        pass


class IRolRepository(ABC):
    @abstractmethod
    def listar(self):
        pass

    @abstractmethod
    def obtener_por_id(self, rol_id):
        pass


class DjangoUsuarioRepository(IUsuarioRepository):
    def listar(self):
        return Usuario.objects.select_related("rol").order_by("usuario_id")

    def obtener_por_id(self, usuario_id):
        return (
            Usuario.objects.select_related("rol")
            .filter(usuario_id=usuario_id).first()
        )

    def obtener_por_email(self, email):
        return Usuario.objects.filter(email__iexact=email).first()

    def crear(self, usuario):
        usuario.save(force_insert=True)
        return usuario

    def actualizar(self, usuario, campos):
        usuario.save(update_fields=campos)
        return usuario


class DjangoRolRepository(IRolRepository):
    def listar(self):
        return Rol.objects.order_by("rol_id")

    def obtener_por_id(self, rol_id):
        return Rol.objects.filter(rol_id=rol_id).first()