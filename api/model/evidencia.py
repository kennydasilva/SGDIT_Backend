from django.db import models
from .denuncia import Denuncia


class Evidencia(models.Model):

    denuncia = models.OneToOneField(
        Denuncia,
        on_delete=models.CASCADE,
        related_name='evidencia'
    )

    caminho_ficheiro = models.FileField(
        upload_to=upload_evidencia_path
    )

    data_captura = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidencia {self.id}"
    


    def upload_evidencia_path(instance, filename):
        return f"denuncias/{instance.denuncia.id}/evidencias/{filename}"