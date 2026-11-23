
from rest_framework import serializers


class ValidarTokenInternoSerializer(serializers.Serializer):
    token = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=False,
        max_length=512
    )


class ResolverUsuariosInternoSerializer(serializers.Serializer):
    usuarios_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=True,
        allow_empty=False,
        max_length=100
    )
