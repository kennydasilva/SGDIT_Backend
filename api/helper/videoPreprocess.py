import subprocess
import os
import logging
import cv2

logger = logging.getLogger(__name__)


def preprocessar_video(caminho_video, largura_alvo=640, fps_alvo=20):
    """
    Reduz resolução e fps do vídeo de entrada ANTES da análise frame a frame
    começar. É o maior ganho de tempo possível: menos frames no total e cada
    frame mais pequeno para o YOLO processar, em vez de continuar a decodificar
    o vídeo original (às vezes 1080p/30fps de um telemóvel) frame a frame.

    Nunca aumenta resolução/fps (só reduz). Se o pré-processamento falhar por
    qualquer razão, devolve o caminho original — a análise continua a
    funcionar, só sem este ganho de velocidade.
    """
    if not caminho_video or not os.path.exists(caminho_video):
        return caminho_video

    cap = cv2.VideoCapture(caminho_video)
    fps_original = cap.get(cv2.CAP_PROP_FPS)
    largura_original = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    cap.release()

    if not fps_original or fps_original <= 0:
        fps_original = 30

    fps_destino = min(fps_alvo, round(fps_original))

    # Já é pequeno e com poucos fps - nada a ganhar em pré-processar
    if largura_original and largura_original <= largura_alvo and fps_original <= fps_alvo:
        return caminho_video

    base, ext = os.path.splitext(caminho_video)
    saida = f"{base}_pre{ext}"

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", caminho_video,
                "-vf", f"scale='min({largura_alvo},iw)':'-2'",
                "-r", str(fps_destino),
                "-an",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                saida,
            ],
            check=True,
            capture_output=True,
        )
        return saida
    except Exception as e:
        logger.error(f"Erro ao pré-processar vídeo {caminho_video}, a usar original: {e}")
        return caminho_video
