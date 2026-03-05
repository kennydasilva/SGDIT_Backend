from rest_framework import serializers
from api.model.user import Cidadao,PT,Admin
from api.models import Utilizador


class UtilizadorSerializer(serializers.ModelSerializer):

    class Meta:
        model=Utilizador
        fields=[
            "id",
            "nome",
            "email",
            "role"
        ]



class CidadaoSerializer(serializers.ModelSerializer):

    class Meta:
        model=Cidadao
        fields=[
            "id",
            "utilizador",
            "numero_denuncias"
        ]

class PTSerializer(serializers.ModelSerializer):

    Utilizador=serializers.StringRelatedField()

    class Meta:
        model= PT
        fields=[
            "id",
            "utilizador",
            "numero_agente"
            "localizacao"
        ]

