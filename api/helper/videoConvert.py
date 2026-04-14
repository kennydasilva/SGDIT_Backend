import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def converter_video_para_browser(caminho_video):
    """
    Converte vídeo (ex: XVID) para MP4 compatível com browser (H.264 + AAC)
    sem alterar estrutura do sistema.
    """
    if not os.path.exists(caminho_video):
        logger.error(f"Arquivo de vídeo não encontrado: {caminho_video}")
        return None
    
    if os.path.getsize(caminho_video) == 0:
        logger.error(f"Arquivo de vídeo está vazio: {caminho_video}")
        return None
    
    base, _ = os.path.splitext(caminho_video)
    output_browser = f"{base}_browser.mp4"

    try:
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", caminho_video,

           
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",

            
            "-c:a", "aac",
            "-b:a", "128k",

           
            "-movflags", "+faststart",

            output_browser
        ], check=True)
        return output_browser
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao converter vídeo {caminho_video}: {e}")
        return None