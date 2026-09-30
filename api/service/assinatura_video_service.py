import logging
import subprocess
from collections import defaultdict

import cv2
import numpy as np
from django.db.models import Q

from api.model.assinatura_video import AssinaturaFrame
from api.model.evidencia import Evidencia

logger = logging.getLogger(__name__)

# Medido (2026-09-30): 3 min de vídeo 1080p ~5,5 s; o mesmo vídeo cortado a
# meio (1 min) e recomprimido noutra resolução -> 60/60 frames reconhecidos.
DISTANCIA_MAXIMA = 6       # bits diferentes (em 64) para dois frames contarem como iguais
MIN_FRAMES_IGUAIS = 3      # vídeos muito curtos: não ligar por 1-2 frames
PROPORCAO_MINIMA = 0.5     # metade dos frames do vídeo novo têm de existir no outro

_LARGURA, _ALTURA = 64, 36


def _sem_sinal(h):
    return h + (1 << 64) if h < 0 else h


def _com_sinal(h):
    return h - (1 << 64) if h >= (1 << 63) else h


def _bandas(h):
    return [(h >> (16 * k)) & 0xFFFF for k in range(4)]


def _distancia(a, b):
    return bin(a ^ b).count("1")


def _dhash(frame_cinzento):
    r = cv2.resize(frame_cinzento, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (r[:, 1:] > r[:, :-1]).flatten()
    valor = 0
    for b in bits:
        valor = (valor << 1) | int(b)
    return valor


class AssinaturaVideoService:
    """
    Regra decidida com o utilizador: o mesmo ficheiro (bytes iguais) é
    recusado no envio (SHA-256); um vídeo visualmente igual a outro já
    enviado (cortado, recomprimido, outra resolução) NÃO é recusado - fica
    ligado à denúncia anterior como relacionada, e o agente decide.
    """

    @staticmethod
    def calcular(caminho_video):
        """1 frame por segundo, reduzido a 64x36 cinzento pelo ffmpeg."""
        processo = subprocess.run(
            [
                "ffmpeg", "-loglevel", "error", "-i", caminho_video,
                "-vf", f"fps=1,scale={_LARGURA}:{_ALTURA},format=gray",
                "-f", "rawvideo", "-",
            ],
            capture_output=True,
            timeout=300,
            check=True,
        )
        frames = np.frombuffer(processo.stdout, np.uint8)
        frames = frames[: len(frames) - len(frames) % (_LARGURA * _ALTURA)]
        return [_dhash(f) for f in frames.reshape(-1, _ALTURA, _LARGURA)]

    @staticmethod
    def guardar(evidencia, hashes):
        AssinaturaFrame.objects.bulk_create([
            AssinaturaFrame(
                evidencia=evidencia,
                hash=_com_sinal(h),
                **{f"b{k}": v for k, v in enumerate(_bandas(h))},
            )
            for h in hashes
        ])

    @staticmethod
    def encontrar_semelhante(hashes, excluir_evidencia_id):
        """Evidência de outra denúncia com o mesmo conteúdo visual, ou None.
        Devolve a que tem mais frames em comum."""
        if len(hashes) < MIN_FRAMES_IGUAIS:
            return None

        bandas_novas = [set() for _ in range(4)]
        for h in hashes:
            for k, v in enumerate(_bandas(h)):
                bandas_novas[k].add(v)

        candidatos = (
            AssinaturaFrame.objects
            .filter(
                Q(b0__in=bandas_novas[0]) | Q(b1__in=bandas_novas[1])
                | Q(b2__in=bandas_novas[2]) | Q(b3__in=bandas_novas[3])
            )
            .exclude(evidencia_id=excluir_evidencia_id)
            .values_list("evidencia_id", "hash")
        )

        por_evidencia = defaultdict(list)
        for evidencia_id, h in candidatos:
            por_evidencia[evidencia_id].append(_sem_sinal(h))

        melhor_id, melhor_iguais = None, 0
        for evidencia_id, existentes in por_evidencia.items():
            iguais = sum(
                1 for h in hashes
                if any(_distancia(h, e) <= DISTANCIA_MAXIMA for e in existentes)
            )
            if iguais > melhor_iguais:
                melhor_id, melhor_iguais = evidencia_id, iguais

        if melhor_iguais >= max(MIN_FRAMES_IGUAIS, PROPORCAO_MINIMA * len(hashes)):
            return Evidencia.objects.select_related("denuncia").get(id=melhor_id)
        return None

    @staticmethod
    def localizacao_contradiz(denuncia, outra):
        """Os dois locais declarados para o mesmo vídeo não batem certo:
        jurisdições diferentes ou mais de 300 m de distância."""
        from api.service.duplicados_service import RAIO_METROS, distancia_metros

        if denuncia.admin_responsavel_id != outra.admin_responsavel_id:
            return True
        if None in (denuncia.latitude, denuncia.longitude, outra.latitude, outra.longitude):
            return False
        return distancia_metros(denuncia.latitude, denuncia.longitude, outra.latitude, outra.longitude) > RAIO_METROS

    @staticmethod
    def processar(denuncia):
        """
        Calcula e guarda a assinatura do vídeo da denúncia e, se for igual
        ao de outra denúncia, liga-a como relacionada. Corre no worker, antes
        da análise por IA. Best-effort: nunca impede a análise.
        """
        try:
            evidencia = Evidencia.objects.filter(denuncia=denuncia).first()
            if not evidencia or not evidencia.caminho_ficheiro:
                return

            # Tentativa repetida do Celery: já calculado, não repetir.
            if evidencia.assinaturas.exists():
                return

            hashes = AssinaturaVideoService.calcular(evidencia.caminho_ficheiro.path)
            AssinaturaVideoService.guardar(evidencia, hashes)

            semelhante = AssinaturaVideoService.encontrar_semelhante(hashes, evidencia.id)
            if not semelhante or semelhante.denuncia_id == denuncia.id:
                return

            outra = semelhante.denuncia
            denuncia.video_semelhante_a = outra
            # Liga ao grupo (sempre à principal), se ainda não estiver ligada
            # por ser a mesma infração.
            if not denuncia.denuncia_principal_id:
                denuncia.denuncia_principal_id = outra.denuncia_principal_id or outra.id

            # Mesmo vídeo declarado noutro local: provável denúncia falsa.
            # Decisão do utilizador: o posto da denúncia original fica com
            # ela (o vídeo é dele), o outro posto não é envolvido.
            if AssinaturaVideoService.localizacao_contradiz(denuncia, outra):
                denuncia.localizacao_contraditoria = True
                denuncia.admin_responsavel_id = outra.admin_responsavel_id

            denuncia.save(update_fields=[
                "video_semelhante_a", "denuncia_principal",
                "localizacao_contraditoria", "admin_responsavel",
            ])

            from api.service.notificacao_service import NotificacaoService
            NotificacaoService.denuncia_relacionada(denuncia, "VIDEO_SEMELHANTE")

        except Exception:
            logger.exception("Falha ao calcular a assinatura visual da denúncia %s", denuncia.id)
