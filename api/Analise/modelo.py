from ultralytics import YOLO

_modelo = None


def obter_modelo():
    """
    Devolve uma instância partilhada do modelo YOLO, carregada uma única vez
    por processo (worker Celery). Antes, cada denúncia processada recarregava
    o modelo do disco do zero, o que soma tempo desnecessário a cada análise.
    """
    global _modelo

    if _modelo is None:
        _modelo = YOLO("yolov8n.pt")

    return _modelo
