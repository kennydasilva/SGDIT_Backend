import json
import logging
import time

import jwt
import requests
from django.core.cache import cache

from api.service.configuracao_service import ConfiguracaoService

logger = logging.getLogger(__name__)

_CACHE_KEY_ACCESS_TOKEN = "firebase_fcm_access_token"
_TOKEN_TTL_SEGUNDOS = 3300  # tokens do Google duram 1h; renovamos aos 55min
_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_TOKEN_URL = "https://oauth2.googleapis.com/token"


class FirebaseService:
    """
    Envio de notificações push (Firebase Cloud Messaging, API HTTP v1) para
    o token registado de um utilizador - usado para avisar o Admin do posto
    responsável quando é reportado um acidente na jurisdição dele.

    Autenticação feita à mão (assinar um JWT com a service account e trocar
    por um access token OAuth2) para não precisar da dependência pesada
    `google-auth`: já temos `PyJWT` e `cryptography` no projeto, suficientes
    para assinar RS256.

    Best-effort: nunca lança exceção - uma falha ao notificar não pode
    impedir a denúncia de ser criada, o Admin continua a poder ver o
    acidente na listagem mesmo sem a notificação chegar.
    """

    @staticmethod
    def _obter_credenciais():
        valor = ConfiguracaoService.obter_valor("FIREBASE_SERVICE_ACCOUNT_JSON")
        if not valor:
            return None

        try:
            return json.loads(valor)
        except (TypeError, ValueError):
            logger.error("FIREBASE_SERVICE_ACCOUNT_JSON configurado não é um JSON válido")
            return None

    @staticmethod
    def _obter_access_token(credenciais):
        token_em_cache = cache.get(_CACHE_KEY_ACCESS_TOKEN)
        if token_em_cache:
            return token_em_cache

        agora = int(time.time())
        payload = {
            "iss": credenciais["client_email"],
            "sub": credenciais["client_email"],
            "scope": _FCM_SCOPE,
            "aud": _TOKEN_URL,
            "iat": agora,
            "exp": agora + 3600,
        }

        jwt_assinado = jwt.encode(payload, credenciais["private_key"], algorithm="RS256")

        resposta = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt_assinado,
            },
            timeout=10,
        )
        resposta.raise_for_status()

        access_token = resposta.json()["access_token"]
        cache.set(_CACHE_KEY_ACCESS_TOKEN, access_token, _TOKEN_TTL_SEGUNDOS)
        return access_token

    @staticmethod
    def enviar_notificacao(token, titulo, corpo, dados=None):
        """
        Envia uma notificação push para um único dispositivo/token.
        Devolve True se enviada com sucesso, False caso contrário (falta de
        configuração, utilizador sem token registado, erro do provedor,
        etc.) - nunca lança exceção.
        """
        if not token:
            return False

        credenciais = FirebaseService._obter_credenciais()
        if not credenciais:
            logger.warning("Firebase não configurado (falta FIREBASE_SERVICE_ACCOUNT_JSON) - notificação não enviada")
            return False

        try:
            access_token = FirebaseService._obter_access_token(credenciais)

            projeto_id = credenciais["project_id"]
            url = f"https://fcm.googleapis.com/v1/projects/{projeto_id}/messages:send"

            mensagem = {
                "message": {
                    "token": token,
                    "notification": {"title": titulo, "body": corpo},
                    "data": {k: str(v) for k, v in (dados or {}).items()},
                }
            }

            resposta = requests.post(
                url,
                json=mensagem,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resposta.raise_for_status()
            return True

        except Exception:
            logger.exception("Falha ao enviar notificação Firebase")
            return False
