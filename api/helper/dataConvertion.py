from datetime import datetime

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