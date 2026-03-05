from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .denuncia import Denuncia

class Evidencia (AbstractBaseUser):

    denucia=models.OneToOneField(
        Denuncia,
        on_delete=models.CASCADE,
        related_name='evidencia'
    )

    tipo=models.CharField(max_length=50)

    caminho_ficheiro=models.FileField(
        upload_to="evidencias/"
    )

    data_captura=models.DateTimeField()

    def __str__(self):
        return f"Evidencia {self.id}"
    

   