from django.db import models
from django.contrib.auth.models import AbstractUser


class Utilizador(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Administrador"
        PT = "PT", "PoliciaTransito"
        CIDADAO = "CIDADAO", "Cidadao"

    nome = models.CharField(max_length=150)
    numero = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    data_registo = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
    
class Cidadao(models.Model):

    utilizador = models.OneToOneField(
        Utilizador,
        on_delete=models.CASCADE,
        related_name="cidadao"
    )

    numero_denuncias = models.IntegerField(default=0)

    def __str__(self):
        return self.utilizador.nome
    

    
class Admin(models.Model):

    utilizador = models.OneToOneField(
        Utilizador,
        on_delete=models.CASCADE,
        related_name="admin"
    )

    posto = models.CharField(max_length=100)

    def __str__(self):
        return self.utilizador.nome
    

class PT(models.Model):

    utilizador = models.OneToOneField(
        Utilizador,
        on_delete=models.CASCADE,
        related_name="pt"
    )

    admin=models.ForeignKey(
        Admin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pts"
    )

    numero_agente = models.CharField(max_length=50)
    localizacao = models.CharField(max_length=255)

    def __str__(self):
        return f"Agente {self.numero_agente}"