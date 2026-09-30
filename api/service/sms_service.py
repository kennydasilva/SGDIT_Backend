import logging
import re
import unicodedata

import requests

from api.service.configuracao_service import ConfiguracaoService

logger = logging.getLogger(__name__)

_URL_ENVIO = "https://api.mozesms.com/sms/send"


class SmsService:
    """
    Envio de SMS real (telecom) via MozeSMS - gateway moçambicano, chega a
    qualquer telemóvel sem app nem browser aberto. Usado para avisar o
    Admin do posto responsável quando é reportado um acidente na
    jurisdição dele - só o Admin, é ele que designa o agente para o local.

    Credenciais lidas de Configurações (encriptadas), nunca de variáveis de
    ambiente: `MOZESMS_API_KEY`, `MOZESMS_API_SECRET` e, opcional,
    `MOZESMS_SENDER_ID` (nome de remetente aprovado na MozeSMS; sem ele a
    MozeSMS usa o remetente por omissão dela).

    Best-effort: nunca lança exceção - uma falha ao enviar não pode impedir
    a denúncia de ser criada; o acidente continua visível na lista de
    acidentes do Admin mesmo sem o SMS chegar.
    """

    @staticmethod
    def normalizar_numero(numero):
        """
        Converte um número moçambicano para o formato internacional sem `+`
        que a MozeSMS exige (ex: "+258 84 123 4567" -> "258841234567").
        Aceita também o número local de 9 dígitos ("841234567").
        Devolve None se não for um número de telemóvel moçambicano válido.
        """
        if not numero:
            return None

        digitos = re.sub(r"\D", "", str(numero))

        if len(digitos) == 9:
            digitos = "258" + digitos

        if re.fullmatch(r"258[89]\d{8}", digitos):
            return digitos

        return None

    @staticmethod
    def _sem_acentos(texto):
        # Acentos (ã, ç, é...) forçam codificação Unicode: 70 caracteres por
        # SMS em vez de 160 - a mesma mensagem passaria a custar 2-3 SMS.
        return (
            unicodedata.normalize("NFKD", texto)
            .encode("ascii", "ignore")
            .decode("ascii")
        )

    @staticmethod
    def enviar_sms(numero, mensagem):
        """
        Envia um SMS para um número. Devolve True se a MozeSMS aceitou o
        envio, False caso contrário (falta de configuração, número
        inválido, sem créditos, erro do provedor, etc.).
        """
        destino = SmsService.normalizar_numero(numero)
        if not destino:
            logger.warning("SMS não enviado: número inválido ou em falta (%r)", numero)
            return False

        api_key = ConfiguracaoService.obter_valor("MOZESMS_API_KEY")
        api_secret = ConfiguracaoService.obter_valor("MOZESMS_API_SECRET")
        if not api_key or not api_secret:
            logger.warning("MozeSMS não configurado (falta MOZESMS_API_KEY/MOZESMS_API_SECRET) - SMS não enviado")
            return False

        corpo = {"phone": destino, "message": SmsService._sem_acentos(mensagem)}

        sender_id = ConfiguracaoService.obter_valor("MOZESMS_SENDER_ID")
        if sender_id:
            corpo["sender_id"] = sender_id

        try:
            resposta = requests.post(
                _URL_ENVIO,
                json=corpo,
                headers={"X-API-Key": api_key, "X-API-Secret": api_secret},
                timeout=15,
            )
            dados = resposta.json() if resposta.content else {}

            if resposta.status_code == 200 and dados.get("success"):
                return True

            logger.error("MozeSMS recusou o envio (HTTP %s): %s", resposta.status_code, dados)
            return False

        except Exception:
            logger.exception("Falha ao enviar SMS via MozeSMS")
            return False
