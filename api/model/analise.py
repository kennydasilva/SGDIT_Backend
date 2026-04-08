from django.db import models
from .denuncia import Denuncia



class ResultadoAnalise(models.Model):

    denuncia = models.OneToOneField(
        Denuncia,
        on_delete=models.CASCADE,
        related_name='resultado_analise',
    
        
    )


    caminho_ficheiro_processado=models.FileField(
        upload_to="videos_processados/",
        null=True,
        blank=True
    )

    descricao=models.CharField(max_length=255, null=True, blank=True)
    codigo_legal=models.CharField(max_length=50, null=True, blank=True)

    confianca = models.FloatField()
    data_analise = models.DateTimeField(auto_now_add=True)

    infracao_detectada = models.BooleanField()

    def __str__(self):
        return f"Resultado Analise {self.id}"