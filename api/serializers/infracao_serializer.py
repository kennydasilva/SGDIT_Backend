from rest_framework import serializers
from api.models import TipoInfracao


class TipoInfracaoSerializer(serializers.ModelSerializer):

    class Meta:
        model = TipoInfracao
        fields = [
            "id",
            "descricao",
            "codigo_legal"
        ]