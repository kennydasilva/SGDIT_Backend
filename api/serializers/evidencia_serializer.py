from rest_framework import serializers


class EvidenciaCreateSerializer(serializers.Serializer):
    denuncia_id = serializers.IntegerField()
    caminho_ficheiro = serializers.FileField()


class EvidenciaResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    denuncia_id = serializers.IntegerField()
    caminho_ficheiro = serializers.CharField()
    data_captura = serializers.DateTimeField()