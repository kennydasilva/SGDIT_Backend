from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .user import Cidadao, PT, Admin

class Denuncia(models.Model):

    class Estado(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        VALIDADA = "VALIDADA", "Validada"
        REJEITADA = "REJEITADA", "Rejeitada"
        APROVADA = "APROVADA", "Aprovada"
        ARQUIVADA = "ARQUIVADA", "Arquivada"
        # Só para ACIDENTE, que não passa por análise de vídeo nem pela
        # fila de validação do PT: vai directo ao Admin do posto da zona.
        ENCAMINHADA = "ENCAMINHADA", "Encaminhada ao posto"
        EM_ATENDIMENTO = "EM_ATENDIMENTO", "Agente designado"
       

    cidadao = models.ForeignKey(
        Cidadao,
        on_delete=models.CASCADE,
        related_name='denuncias'
    )

    pt = models.ForeignKey(
        PT,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='denuncias'
    )

    data_registo = models.DateTimeField(auto_now_add=True)
    # Actualizado sempre que a denúncia é gravada (ex: PT decide o `estado`).
    # Usado para calcular o tempo médio de resposta em Relatórios - sem isto
    # não há como saber quanto tempo uma denúncia ficou pendente.
    atualizado_em = models.DateTimeField(auto_now=True)
    matricula = models.CharField(max_length=255, null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDENTE
    )

    descricao=models.CharField(max_length=255, null=True, blank=True)
    descricao_pt=models.CharField(max_length=255, null=True, blank=True)
    codigo_legal=models.CharField(max_length=50, null=True, blank=True)
    sentido_direccao=models.CharField(max_length=255, null=True, blank=True)

    class tipoInfracao(models.TextChoices):
        CONTRAMAO = "CONTRAMAO", "contramao"
        PARADO = "PARADO", "parado"
        VELOCIDADE = "VELOCIDADE", "velocidade"
        ACIDENTE = "ACIDENTE", "acidente"

    tipo_infracao = models.CharField(
    max_length=20,
    choices=tipoInfracao.choices,
    null=True,
    blank=True
    )

    localizacao = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Só usado para tipo_infracao=ACIDENTE: posto cuja jurisdição cobre a
    # localização do acidente (via ViaJurisdicao), determinado
    # automaticamente na criação. É o Admin deste posto que recebe a
    # notificação e designa o(s) agente(s) que vão ao local - nunca se
    # notifica todos os agentes, cada posto só vê e decide sobre a sua
    # própria jurisdição.
    admin_responsavel = models.ForeignKey(
        Admin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="denuncias_acidente"
    )

    def __str__(self):
        return f"Denuncia {self.id}"