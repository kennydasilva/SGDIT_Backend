from django.db import models
from django.contrib.auth.models import AbstractBaseUser

class TipoInfracao(models.Model):

    descricao=models.CharField(max_length=255)
    codigo_legal=models.CharField(max_length=50)
    class tipo(models.TextChoices):
        CONTRAMAO = "CONTRAMAO", "contramao"
        PARADO = "PARADO", "parado"
        VELOCIDADE = "VELOCIDADE", "velocidade"
       

    def __str__(self):
        return self.descricao