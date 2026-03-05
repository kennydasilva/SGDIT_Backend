from django.db import models
from django.contrib.auth.models import AbstractBaseUser

class Utilizador (AbstractBaseUser):

    class Role(models.TextChoices):
        SUPER_ADMIN="SUPER_ADMIN", "Super Admin"
        Admin="ADMIN", "Administrador"
        PT="PT", "PoliciaTransito"
        CIDADAO="CIDADAO", "Cidadao"

    
    nome=models.CharField(max_length=150)
    email=models.EmailField(unique=True)
    role=models.CharField(max_length=20, choices=Role.choices)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    

class Cidadao(models.Model):

    utilizador=models.OneToOneField(
        Utilizador,
        on_delete=models.CASCADE,
        related_name='cidadao'
    )

    numero_denuncias=models.IntegerField(default=0)

    def __str__(self):
        return self.utilizador.nome
    

class PT(models.Model):

    utilizador=models.OneToOneField(
        Utilizador,
        on_delete=models.CASCADE,
        related_name='pt'
    )

    numero_agente=models.CharField(max_length=50)
    localizacao=models.CharField(max_length=255)

    def __str__(self):
        return f"Agente {self.numero_agente}"
    

class Admin(models.Model):

    utilizador=models.OneToOneField(
        Utilizador,
        on_delete=models.CASCADE,
        related_name='admin'
    )

    posto=models.CharField(max_length=100)

    def __str__(self):
        return f"Admin {self.utilizador.nome}"