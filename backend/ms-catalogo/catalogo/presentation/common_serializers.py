"""Validación de campos no reconocidos, reutilizada del monolito."""

from rest_framework import serializers


class CamposPermitidosSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            return super().to_internal_value(data)

        desconocidos = set(data) - set(self.fields)
        if desconocidos:
            raise serializers.ValidationError({
                campo: ["Este campo no está permitido."]
                for campo in sorted(desconocidos)
            })
        return super().to_internal_value(data)
