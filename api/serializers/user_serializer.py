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

    utilizador=serializers.StringRelatedField()

    class Meta:
        model= PT
        fields=[
            "id",
            "utilizador",
            "numero_agente",
            "localizacao",
            "admin_id"
        ]

class PTCreateSerializer(serializers.Serializer):

    nome = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()
    numero_agente = serializers.CharField()
    localizacao = serializers.CharField()
    admin_id = serializers.IntegerField()


class PTResponseSerializer(serializers.Serializer):

    id = serializers.IntegerField()
    nome = serializers.CharField()
    email = serializers.EmailField()
    numero_agente = serializers.CharField()
    localizacao = serializers.CharField()
    admin_id = serializers.IntegerField()

class CriarAdminSerializer(serializers.Serializer):

    nome = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()
    posto = serializers.CharField()

class AdminResponseSerializer(serializers.Serializer):

    id = serializers.IntegerField()
    nome = serializers.CharField()
    email = serializers.EmailField()
    posto = serializers.CharField()