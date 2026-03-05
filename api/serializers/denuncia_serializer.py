from rest_framework import serializers
from api.models import Denuncia
from .analise_serializer import ResultadoAnaliseSerializer
from .evidencia_serializer import EvidenciaSerializer


class DenunciaSerializer(serializers.ModelSerializer):

    resultado_analise = ResultadoAnaliseSerializer(read_only=True)

    evidencia = EvidenciaSerializer(read_only=True)

    class Meta:
        model = Denuncia
        fields = [
            "id",
            "cidadao",
            "pt",
            "data_registo",
            "estado",
            "localizacao",
            "resultado_analise",
            "evidencia"
        ]

class CriarDenunciaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Denuncia
        fields = [
            "localizacao"
        ]