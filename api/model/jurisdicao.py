from django.db import models
from .user import Admin


class ViaJurisdicao(models.Model):
    """
    Uma via/estrada/avenida atribuída à jurisdição de um posto (Admin).
    Ex: posto Mavalane -> Hulene, Xiquelene, Estrada do Aeroporto.
    Guardamos o place_id do Google (estável, melhor para casar do que
    comparar texto livre) e, opcionalmente, a geometria da via para a
    desenhar no mapa.
    """

    admin = models.ForeignKey(
        Admin,
        on_delete=models.CASCADE,
        related_name="vias_jurisdicao"
    )

    nome_via = models.CharField(max_length=255)
    place_id = models.CharField(max_length=255)
    geometria = models.JSONField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("admin", "place_id")

    def __str__(self):
        return f"{self.nome_via} ({self.admin})"
