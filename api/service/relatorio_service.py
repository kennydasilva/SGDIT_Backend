from datetime import datetime, time, timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from api.model.denuncia import Denuncia

MESES_HISTORICO = 6
MESES_MAXIMO_GRAFICO = 24

# Estados em que a denúncia ainda espera resposta de alguém. Acidente
# "encaminhado" ao posto só conta como respondido quando o Admin designa
# um agente (EM_ATENDIMENTO).
SEM_RESPOSTA = [Denuncia.Estado.PENDENTE, Denuncia.Estado.ENCAMINHADA]

# Decisões tomadas por um agente (a negativa do agente grava ARQUIVADA).
ESTADOS_DECISAO_AGENTE = [Denuncia.Estado.APROVADA, Denuncia.Estado.ARQUIVADA, Denuncia.Estado.REJEITADA]


def _horas(duracao):
    return round(duracao.total_seconds() / 3600, 1) if duracao else None


def _pct(parte, total):
    return round(parte * 100 / total, 1) if total else 0.0


class RelatorioService:
    """
    Relatórios com filtros (período, posto, tipo, estado). O Super Admin vê
    tudo; o Admin só o seu posto (o controlador força `admin_id`).
    """

    # ---- filtros ---------------------------------------------------------

    @staticmethod
    def ler_filtros(params, admin_forcado=None):
        """Converte os parâmetros do pedido num dicionário de filtros.
        Datas no formato AAAA-MM-DD (inclusivas). `admin_id` aceita também
        "sem_posto" (denúncias fora de qualquer jurisdição)."""
        def data(nome):
            valor = params.get(nome)
            if not valor:
                return None
            try:
                return datetime.strptime(valor, "%Y-%m-%d").date()
            except ValueError:
                return None

        admin_param = params.get("admin_id")
        sem_posto = admin_forcado is None and admin_param == "sem_posto"
        if admin_forcado is not None:
            admin_id = admin_forcado
        elif admin_param and admin_param.isdigit():
            admin_id = int(admin_param)
        else:
            admin_id = None

        return {
            "data_inicio": data("data_inicio"),
            "data_fim": data("data_fim"),
            "admin_id": admin_id,
            "sem_posto": sem_posto,
            "tipo": params.get("tipo") or None,
            "estado": params.get("estado") or None,
        }

    @staticmethod
    def filtrar(filtros):
        qs = Denuncia.objects.all()
        tz = timezone.get_current_timezone()
        if filtros.get("data_inicio"):
            qs = qs.filter(data_registo__gte=timezone.make_aware(datetime.combine(filtros["data_inicio"], time.min), tz))
        if filtros.get("data_fim"):
            qs = qs.filter(data_registo__lte=timezone.make_aware(datetime.combine(filtros["data_fim"], time.max), tz))
        if filtros.get("sem_posto"):
            qs = qs.filter(admin_responsavel__isnull=True)
        elif filtros.get("admin_id"):
            qs = qs.filter(admin_responsavel_id=filtros["admin_id"])
        if filtros.get("tipo"):
            qs = qs.filter(tipo_infracao=filtros["tipo"])
        if filtros.get("estado"):
            qs = qs.filter(estado=filtros["estado"])
        return qs

    # ---- resumo ----------------------------------------------------------

    @staticmethod
    def obter_resumo(filtros=None):
        filtros = filtros or {}
        qs = RelatorioService.filtrar(filtros)
        total = qs.count()

        por_estado = {estado: 0 for estado, _ in Denuncia.Estado.choices}
        for linha in qs.values("estado").annotate(total=Count("id")):
            if linha["estado"]:
                por_estado[linha["estado"]] = linha["total"]

        por_tipo_infracao = {tipo: 0 for tipo, _ in Denuncia.tipoInfracao.choices}
        for linha in qs.exclude(tipo_infracao__isnull=True).values("tipo_infracao").annotate(total=Count("id")):
            por_tipo_infracao[linha["tipo_infracao"]] = linha["total"]

        pendentes = sum(por_estado.get(e, 0) for e in SEM_RESPOSTA)

        tempo_medio = (
            qs.exclude(estado__in=SEM_RESPOSTA)
            .annotate(tempo=F("atualizado_em") - F("data_registo"))
            .aggregate(media=Avg("tempo"))["media"]
        )

        return {
            "filtros": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in filtros.items()},
            "total_denuncias": total,
            "taxa_resolucao": _pct(total - pendentes, total),
            "tempo_medio_resposta_horas": _horas(tempo_medio),
            "por_estado": por_estado,
            "por_tipo_infracao": por_tipo_infracao,
            "por_mes": RelatorioService._contagem_por_mes(qs, filtros),
            "por_posto": RelatorioService._por_posto(qs),
            "agentes": RelatorioService._agentes(qs),
            "acidentes": RelatorioService._acidentes(qs),
            "qualidade": RelatorioService._qualidade(qs, total),
        }

    @staticmethod
    def _contagem_por_mes(qs, filtros):
        """Meses do período filtrado (máx. 24) ou, sem período, os últimos 6
        - incluindo meses sem denúncias, para o gráfico não saltar meses."""
        fim = filtros.get("data_fim") or timezone.localtime().date()
        inicio = filtros.get("data_inicio")

        meses = []
        cursor = fim.replace(day=1)
        limite = MESES_MAXIMO_GRAFICO if inicio else MESES_HISTORICO
        while len(meses) < limite:
            meses.append(cursor)
            if inicio and cursor <= inicio.replace(day=1):
                break
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        meses.reverse()

        contagens = {
            linha["mes"].strftime("%Y-%m"): linha["total"]
            for linha in qs.annotate(mes=TruncMonth("data_registo")).values("mes").annotate(total=Count("id"))
            if linha["mes"]
        }
        return [{"mes": m.strftime("%Y-%m"), "total": contagens.get(m.strftime("%Y-%m"), 0)} for m in meses]

    @staticmethod
    def _por_posto(qs):
        tempo = ExpressionWrapper(F("atualizado_em") - F("data_registo"), output_field=DurationField())
        linhas = (
            qs.values("admin_responsavel_id", "admin_responsavel__posto")
            .annotate(
                total=Count("id"),
                sem_resposta=Count("id", filter=Q(estado__in=SEM_RESPOSTA)),
                aprovadas=Count("id", filter=Q(estado=Denuncia.Estado.APROVADA)),
                acidentes=Count("id", filter=Q(tipo_infracao=Denuncia.tipoInfracao.ACIDENTE)),
                tempo_medio=Avg(tempo, filter=~Q(estado__in=SEM_RESPOSTA)),
            )
            .order_by("-total")
        )
        return [
            {
                "admin_id": l["admin_responsavel_id"],
                "posto": l["admin_responsavel__posto"] or "Sem posto (fora das jurisdições)",
                "total": l["total"],
                "aprovadas": l["aprovadas"],
                "acidentes": l["acidentes"],
                "taxa_resolucao": _pct(l["total"] - l["sem_resposta"], l["total"]),
                "tempo_medio_resposta_horas": _horas(l["tempo_medio"]),
            }
            for l in linhas
        ]

    @staticmethod
    def _agentes(qs):
        tempo_decisao = ExpressionWrapper(F("decidido_em") - F("data_registo"), output_field=DurationField())
        linhas = (
            qs.filter(pt__isnull=False, estado__in=ESTADOS_DECISAO_AGENTE)
            .values("pt_id", "pt__utilizador__nome", "pt__numero_agente", "pt__admin__posto")
            .annotate(
                decisoes=Count("id"),
                aprovadas=Count("id", filter=Q(estado=Denuncia.Estado.APROVADA)),
                arquivadas=Count("id", filter=Q(estado__in=[Denuncia.Estado.ARQUIVADA, Denuncia.Estado.REJEITADA])),
                tempo_medio=Avg(tempo_decisao, filter=Q(decidido_em__isnull=False)),
            )
            .order_by("-decisoes")
        )
        return [
            {
                "pt_id": l["pt_id"],
                "nome": l["pt__utilizador__nome"],
                "numero_agente": l["pt__numero_agente"],
                "posto": l["pt__admin__posto"],
                "decisoes": l["decisoes"],
                "aprovadas": l["aprovadas"],
                "arquivadas": l["arquivadas"],
                "tempo_medio_decisao_horas": _horas(l["tempo_medio"]),
            }
            for l in linhas
        ]

    @staticmethod
    def _acidentes(qs):
        acidentes = qs.filter(tipo_infracao=Denuncia.tipoInfracao.ACIDENTE)
        # Cada acidente real conta uma vez: os reportes juntados a outro
        # (relacionadas) contam à parte.
        principais = acidentes.filter(denuncia_principal__isnull=True)
        tempo_designar = ExpressionWrapper(F("designado_em") - F("data_registo"), output_field=DurationField())
        media = principais.filter(designado_em__isnull=False).aggregate(m=Avg(tempo_designar))["m"]
        return {
            "total": principais.count(),
            "reportes_juntados": acidentes.filter(denuncia_principal__isnull=False).count(),
            "sem_posto": principais.filter(admin_responsavel__isnull=True).count(),
            "a_aguardar_agente": principais.filter(estado=Denuncia.Estado.ENCAMINHADA).count(),
            "com_agente": principais.filter(pt__isnull=False).count(),
            "tempo_medio_ate_designar_min": round(media.total_seconds() / 60, 1) if media else None,
        }

    @staticmethod
    def _qualidade(qs, total):
        rejeitadas_ia = qs.filter(estado=Denuncia.Estado.REJEITADA, pt__isnull=True)
        # Rejeitada sem resultado de análise = o vídeo não pôde ser analisado.
        video_ilegivel = rejeitadas_ia.filter(resultado_analise__isnull=True).count()
        testemunhas = (
            qs.filter(denuncia_principal__isnull=False)
            .exclude(tipo_infracao=Denuncia.tipoInfracao.ACIDENTE)
            .count()
        )
        return {
            "rejeitadas_ia": rejeitadas_ia.count() - video_ilegivel,
            "video_ilegivel": video_ilegivel,
            "testemunhas": testemunhas,
            "videos_semelhantes": qs.filter(video_semelhante_a__isnull=False).count(),
            "possiveis_falsas": qs.filter(localizacao_contraditoria=True).count(),
            "taxa_rejeicao_ia": _pct(rejeitadas_ia.count(), total),
        }

    # ---- lista detalhada (exportações) -----------------------------------

    @staticmethod
    def listar_detalhe(filtros):
        return (
            RelatorioService.filtrar(filtros)
            .select_related("admin_responsavel", "pt__utilizador", "resultado_analise")
            .order_by("-data_registo")
        )
