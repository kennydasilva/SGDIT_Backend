from rest_framework import serializers
from api.models import ResultadoAnalise



class ResultadoAnaliseSerializer(serializers.ModelSerializer):


    class Meta:
        model = ResultadoAnalise
        fields = [
            "id",
          
            "confianca",
            "data_analise",
            "infracao_detectada"
        ]