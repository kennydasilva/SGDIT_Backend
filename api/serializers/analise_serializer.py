from rest_framework import serializers
from api.models import ResultadoAnalise
from .infracao_serializer import TipoInfracaoSerializer


class ResultadoAnaliseSerializer(serializers.ModelSerializer):

    tipo_infracao = TipoInfracaoSerializer(read_only=True)

    class Meta:
        model = ResultadoAnalise
        fields = [
            "id",
            "tipo_infracao",
            "confianca",
            "data_analise",
            "infracao_detectada"
        ]