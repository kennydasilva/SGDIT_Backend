from rest_framework import serializers
from api.models import Evidencia


class EvidenciaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Evidencia
        fields = [
            "id",
            "tipo",
            "caminho_ficheiro",
            "data_captura"
        ]

class UploadEvidenciaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Evidencia
        fields = [
            "tipo",
            "caminho_ficheiro",
            "data_captura"
        ]