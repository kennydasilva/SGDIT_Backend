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