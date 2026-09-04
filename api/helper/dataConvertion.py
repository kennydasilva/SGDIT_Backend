import hashlib
from datetime import datetime

def gerar_codigo_cidadao(cidadao_id):
    """
    Código estável e anónimo para um cidadão (ex: 'CID-A3F9B2'), usado em
    listagens públicas/motivacionais (ex: ranking) sem expor nome nem ID
    sequencial. Não reversível para o ID real.
    """
    hash_curto = hashlib.sha256(f"cidadao-{cidadao_id}-ranking".encode()).hexdigest()[:6].upper()
    return f"CID-{hash_curto}"

def formatar_data(data, formato="%d/%m/%Y %H:%M:%S"):
    """Formata uma data para o formato legível"""
    if data:
       
        if isinstance(data, str):
            try:
                data = datetime.fromisoformat(data.replace('Z', '+00:00'))
            except:
                return data
        return data.strftime(formato)
    return None