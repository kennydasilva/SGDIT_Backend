from django.db import models
from .denuncia import Denuncia

def upload_evidencia_path(instance, filename):
        return f"denuncias/{instance.denuncia.id}/evidencias/{filename}"
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

    # Impressão digital do ficheiro: o mesmo ficheiro nunca pode ser usado
    # em duas denúncias. Não é `unique` porque já existem repetidos de
    # antes desta regra (deixados como estão, por decisão do utilizador).
    hash_sha256 = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    def __str__(self):
        return f"Evidencia {self.id}"
    


    