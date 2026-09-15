from datetime import timedelta

from django.db.models import Avg, Count, F
from django.db.models.functions import TruncMonth
from django.utils import timezone

from api.model.denuncia import Denuncia

MESES_HISTORICO = 6


class RelatorioService:

    @staticmethod
    def obter_resumo():
        total = Denuncia.objects.count()

        por_estado = {
            estado: 0 for estado, _ in Denuncia.Estado.choices
        }
        for linha in Denuncia.objects.values("estado").annotate(total=Count("id")):
            if linha["estado"]:
                por_estado[linha["estado"]] = linha["total"]

        por_tipo_infracao = {
            tipo: 0 for tipo, _ in Denuncia.tipoInfracao.choices
        }
        for linha in Denuncia.objects.exclude(tipo_infracao__isnull=True).values("tipo_infracao").annotate(total=Count("id")):
            por_tipo_infracao[linha["tipo_infracao"]] = linha["total"]

        pendentes = por_estado.get(Denuncia.Estado.PENDENTE, 0)
        decididas = total - pendentes
        taxa_resolucao = round((decididas / total) * 100, 1) if total else 0.0

        tempo_medio = (
            Denuncia.objects
            .exclude(estado=Denuncia.Estado.PENDENTE)
            .annotate(tempo_resposta=F("atualizado_em") - F("data_registo"))
            .aggregate(media=Avg("tempo_resposta"))["media"]
        )
        tempo_medio_horas = round(tempo_medio.total_seconds() / 3600, 1) if tempo_medio else None

        return {
            "total_denuncias": total,
            "taxa_resolucao": taxa_resolucao,
            "tempo_medio_resposta_horas": tempo_medio_horas,
            "por_estado": por_estado,
            "por_tipo_infracao": por_tipo_infracao,
            "por_mes": RelatorioService._contagem_por_mes(),
        }

    @staticmethod
    def _contagem_por_mes():
        """
        Últimos MESES_HISTORICO meses (incluindo os sem nenhuma denúncia, para
        o gráfico não "saltar" meses vazios), mais antigo primeiro.
        """
        agora = timezone.now()
        inicio_do_mes_atual = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        meses = []
        cursor = inicio_do_mes_atual
        for _ in range(MESES_HISTORICO):
            meses.append(cursor)
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        meses.reverse()

        contagens = {
            linha["mes"].strftime("%Y-%m"): linha["total"]
            for linha in (
                Denuncia.objects
                .filter(data_registo__gte=meses[0])
                .annotate(mes=TruncMonth("data_registo"))
                .values("mes")
                .annotate(total=Count("id"))
            )
        }

        return [
            {"mes": mes.strftime("%Y-%m"), "total": contagens.get(mes.strftime("%Y-%m"), 0)}
            for mes in meses
        ]
