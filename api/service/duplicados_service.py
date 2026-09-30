import hashlib
import math
from datetime import timedelta

from django.utils import timezone

from api.model.denuncia import Denuncia
from api.model.evidencia import Evidencia

# Regras decididas com o utilizador (2026-09-30):
#  1. O mesmo ficheiro nunca pode ser usado em duas denúncias.
#  2. O mesmo cidadão não pode ter duas denúncias abertas para a mesma
#     matrícula e tipo (num acidente: o mesmo local/hora).
#  3. Cidadãos diferentes a denunciar a mesma infração: a nova fica ligada
#     à primeira ("relacionada"), não é recusada.
#  4. Acidentes: vários reportes a menos de 300 m e 1 hora são o mesmo
#     acidente - juntam-se ao primeiro (um só SMS ao Admin).
RAIO_METROS = 300
JANELA_ACIDENTE = timedelta(hours=1)
JANELA_RELACIONADA = timedelta(hours=24)

ESTADOS_ABERTOS = [
    Denuncia.Estado.PENDENTE,
    Denuncia.Estado.VALIDADA,
    Denuncia.Estado.ENCAMINHADA,
    Denuncia.Estado.EM_ATENDIMENTO,
]


def distancia_metros(lat1, lng1, lat2, lng2):
    """Distância em linha recta (haversine) entre dois pontos."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class DuplicadosService:

    @staticmethod
    def calcular_hash(ficheiro):
        h = hashlib.sha256()
        for bloco in ficheiro.chunks():
            h.update(bloco)
        ficheiro.seek(0)
        return h.hexdigest()

    @staticmethod
    def ficheiro_ja_usado(hash_sha256):
        return Evidencia.objects.filter(hash_sha256=hash_sha256).select_related("denuncia").first()

    @staticmethod
    def _mais_proxima(candidatas, lat, lng):
        if lat is None or lng is None:
            return None

        melhor, melhor_dist = None, None
        for d in candidatas:
            if d.latitude is None or d.longitude is None:
                continue
            dist = distancia_metros(lat, lng, d.latitude, d.longitude)
            if dist <= RAIO_METROS and (melhor_dist is None or dist < melhor_dist):
                melhor, melhor_dist = d, dist
        return melhor

    @staticmethod
    def denuncia_aberta_do_cidadao(cidadao_id, tipo_infracao, matricula, lat, lng):
        """Regra 2: denúncia ainda aberta do mesmo cidadão para a mesma
        coisa. Num acidente (matrícula opcional) compara local e hora."""
        abertas = Denuncia.objects.filter(
            cidadao_id=cidadao_id,
            tipo_infracao=tipo_infracao,
            estado__in=ESTADOS_ABERTOS,
        )

        if tipo_infracao == Denuncia.tipoInfracao.ACIDENTE:
            recentes = abertas.filter(data_registo__gte=timezone.now() - JANELA_ACIDENTE)
            return DuplicadosService._mais_proxima(recentes, lat, lng)

        return abertas.filter(matricula__iexact=matricula).first()

    @staticmethod
    def encontrar_principal(cidadao_id, tipo_infracao, matricula, lat, lng):
        """Regras 3 e 4: a denúncia (de outro cidadão) a que esta se deve
        ligar, ou None. Liga sempre à principal do grupo, nunca a outra
        relacionada."""
        candidatas = Denuncia.objects.filter(
            tipo_infracao=tipo_infracao,
            estado__in=ESTADOS_ABERTOS,
            denuncia_principal__isnull=True,
        ).exclude(cidadao_id=cidadao_id)

        if tipo_infracao == Denuncia.tipoInfracao.ACIDENTE:
            candidatas = candidatas.filter(data_registo__gte=timezone.now() - JANELA_ACIDENTE)
        else:
            if not matricula:
                return None
            candidatas = candidatas.filter(
                matricula__iexact=matricula,
                data_registo__gte=timezone.now() - JANELA_RELACIONADA,
            )

        return DuplicadosService._mais_proxima(candidatas, lat, lng)
