from django.db import models

from .evidencia import Evidencia


class AssinaturaFrame(models.Model):
    """
    Assinatura visual (hash perceptual de 64 bits) de um frame do vídeo de
    uma evidência, 1 por segundo. Sobrevive a cortes, recompressão e mudança
    de resolução - ao contrário do SHA-256 do ficheiro - e serve para ligar
    uma denúncia nova a outra que usou o mesmo vídeo (editado).

    `b0`..`b3` são as 4 bandas de 16 bits do hash, indexadas: dois hashes
    muito próximos partilham quase sempre pelo menos uma banda, o que
    permite encontrar candidatos sem comparar com todos os frames da base.
    """

    evidencia = models.ForeignKey(
        Evidencia,
        on_delete=models.CASCADE,
        related_name="assinaturas"
    )
    # Guardado com sinal (BigIntegerField é int64); ver AssinaturaVideoService.
    hash = models.BigIntegerField()
    b0 = models.IntegerField(db_index=True)
    b1 = models.IntegerField(db_index=True)
    b2 = models.IntegerField(db_index=True)
    b3 = models.IntegerField(db_index=True)

    def __str__(self):
        return f"Frame {self.id} (evidencia {self.evidencia_id})"
