from django.db import models
from api.helper.crypto import encriptar, desencriptar


class ConfiguracaoAPI(models.Model):
    """
    Credenciais de integrações externas (Google Maps, Firebase, etc.),
    geridas pelo Super Admin via UI em vez de variáveis de ambiente.
    O valor é sempre guardado encriptado.

    `publica` distingue chaves seguras para expor ao frontend (ex: chave
    JS do Google Maps, protegida por restrição de domínio na Google Cloud
    Console) de segredos que NUNCA devem sair do backend (ex: credenciais
    de servidor do Firebase Admin SDK).
    """

    chave = models.CharField(max_length=100, unique=True)
    valor_encriptado = models.TextField()
    publica = models.BooleanField(default=False)
    descricao = models.CharField(max_length=255, blank=True, null=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def set_valor(self, valor_plano):
        self.valor_encriptado = encriptar(valor_plano)

    def get_valor(self):
        return desencriptar(self.valor_encriptado)

    def __str__(self):
        return self.chave
