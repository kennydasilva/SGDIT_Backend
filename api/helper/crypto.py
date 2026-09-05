import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings


def _obter_fernet():
    """
    Deriva uma chave Fernet (32 bytes, URL-safe base64) a partir da
    SECRET_KEY do Django, para não precisar de gerir mais um segredo à
    parte só para isto.
    """
    chave_derivada = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    chave_fernet = base64.urlsafe_b64encode(chave_derivada)
    return Fernet(chave_fernet)


def encriptar(valor: str) -> str:
    return _obter_fernet().encrypt(valor.encode()).decode()


def desencriptar(valor_encriptado: str) -> str:
    return _obter_fernet().decrypt(valor_encriptado.encode()).decode()
