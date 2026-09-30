from django.db import models

from .user import Utilizador
from .denuncia import Denuncia


class Notificacao(models.Model):
    """
    Notificação dentro da aplicação, para qualquer utilizador (Cidadão, PT,
    Admin, Super Admin). Criada sempre que há uma actualização relevante
    para esse utilizador - ex: mudança de estado da denúncia do cidadão,
    denúncia nova na fila do agente, acidente na jurisdição do Admin.
    """

    class Tipo(models.TextChoices):
        DENUNCIA_RECEBIDA = "DENUNCIA_RECEBIDA", "Denúncia recebida"
        ESTADO_ALTERADO = "ESTADO_ALTERADO", "Estado da denúncia alterado"
        NOVA_PARA_REVISAO = "NOVA_PARA_REVISAO", "Nova denúncia para revisão"
        ACIDENTE_REPORTADO = "ACIDENTE_REPORTADO", "Acidente reportado"
        AGENTE_DESIGNADO = "AGENTE_DESIGNADO", "Designado para acidente"
        ANALISE_FALHOU = "ANALISE_FALHOU", "Falha na análise do vídeo"

    utilizador = models.ForeignKey(
        Utilizador,
        on_delete=models.CASCADE,
        related_name="notificacoes"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    titulo = models.CharField(max_length=150)
    mensagem = models.CharField(max_length=500)
    denuncia = models.ForeignKey(
        Denuncia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes"
    )
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]
        indexes = [models.Index(fields=["utilizador", "lida"])]

    def __str__(self):
        return f"{self.utilizador_id}: {self.titulo}"
