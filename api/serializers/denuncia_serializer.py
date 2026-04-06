from rest_framework import serializers
from api.models import Denuncia
from .analise_serializer import ResultadoAnaliseSerializer
from .evidencia_serializer import EvidenciaResponseSerializer

class DenunciaCreateSerializer(serializers.Serializer):

    resultado_analise = ResultadoAnaliseSerializer(read_only=True)

    evidencia = EvidenciaResponseSerializer(read_only=True)

    cidadao_id = serializers.IntegerField()
    pt_id = serializers.IntegerField(required=False, allow_null=True)
    matricula = serializers.CharField(max_length=255)
    descricao = serializers.CharField(max_length=255)
    codigo_legal = serializers.CharField(max_length=50)
    tipo_infracao = serializers.ChoiceField(choices=Denuncia.tipoInfracao.choices)
    localizacao = serializers.CharField(max_length=255)
    denuncia_id = serializers.IntegerField()
    caminho_ficheiro = serializers.FileField()


class DenunciaResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cidadao_id = serializers.IntegerField()
    pt_id = serializers.IntegerField(allow_null=True)
    matricula = serializers.CharField()
    estado = serializers.CharField()
    descricao = serializers.CharField()
    descricao_pt = serializers.CharField(allow_null=True)
    codigo_legal = serializers.CharField()
    tipo_infracao = serializers.CharField()
    localizacao = serializers.CharField()
    data_registo = serializers.DateTimeField()