from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .user import Cidadao, PT

class Denuncia(models.Model):

    class Estado(models.TextChoices):
        Pendente="PENDENTE", "Pendente"
        Validada="VALIDADA", "Validada"
        Rejeitada="REJEITADA", "Rejeitada"
        Aprovada="APROVADA", "Aprovada"
        Arquivada="ARQUIVADA", "Arquivada"


    cidadao=models.ForeignKey(
        Cidadao,
        on_delete=models.CASCADE,
        related_name='denuncias'
    )

    pt=models.ForeignKey(
        PT,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='denuncias'
    )

    data_registo=models.DateTimeField(auto_now_add=True)

    estado=models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.Pendente
    )

    localizacao=models.CharField(max_length=255)

    def __str__(self):
        return f"Denucia {self.id}"