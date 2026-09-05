from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .user import Cidadao, PT

class Denuncia(models.Model):

    class Estado(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        VALIDADA = "VALIDADA", "Validada"
        REJEITADA = "REJEITADA", "Rejeitada"
        APROVADA = "APROVADA", "Aprovada"
        ARQUIVADA = "ARQUIVADA", "Arquivada"
       

    cidadao = models.ForeignKey(
        Cidadao,
        on_delete=models.CASCADE,
        related_name='denuncias'
    )

    pt = models.ForeignKey(
        PT,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='denuncias'
    )

    data_registo = models.DateTimeField(auto_now_add=True)
    matricula = models.CharField(max_length=255, null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDENTE
    )

    descricao=models.CharField(max_length=255, null=True, blank=True)
    descricao_pt=models.CharField(max_length=255, null=True, blank=True)
    codigo_legal=models.CharField(max_length=50, null=True, blank=True)
    sentido_direccao=models.CharField(max_length=255, null=True, blank=True)

    class tipoInfracao(models.TextChoices):
        CONTRAMAO = "CONTRAMAO", "contramao"
        PARADO = "PARADO", "parado"
        VELOCIDADE = "VELOCIDADE", "velocidade"

    tipo_infracao = models.CharField(
    max_length=20,
    choices=tipoInfracao.choices,
    null=True,
    blank=True
    )

    localizacao = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Denuncia {self.id}"