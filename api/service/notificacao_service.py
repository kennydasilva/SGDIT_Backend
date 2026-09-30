import logging

from api.model.denuncia import Denuncia
from api.model.notificacao import Notificacao
from api.model.user import PT, Utilizador

logger = logging.getLogger(__name__)

TIPO_LABEL = {
    "CONTRAMAO": "contramão",
    "PARADO": "veículo parado",
    "VELOCIDADE": "excesso de velocidade",
    "ACIDENTE": "acidente de viação",
}

# O que o cidadão lê quando a sua denúncia muda de estado. Chave
# (estado, origem) tem prioridade sobre só o estado - a mesma rejeição
# lê-se de forma diferente se veio da IA ou de um agente.
MENSAGEM_ESTADO_CIDADAO = {
    ("REJEITADA", "IA"): "A análise automática não detectou a infração no vídeo, por isso a denúncia foi rejeitada.",
    ("REJEITADA", "PT"): "Um agente de trânsito reviu a denúncia e rejeitou-a.",
    ("APROVADA", "PT"): "Um agente de trânsito reviu e aprovou a denúncia. Obrigado pela sua colaboração.",
    "VALIDADA": "A análise automática confirmou a infração. A denúncia está agora em revisão por um agente.",
    "REJEITADA": "A denúncia foi rejeitada.",
    "APROVADA": "A denúncia foi aprovada por um agente de trânsito.",
    "ARQUIVADA": "A denúncia foi arquivada.",
    "ENCAMINHADA": "O acidente foi enviado ao posto policial responsável pela zona.",
    "EM_ATENDIMENTO": "Foi designado um agente para o local do acidente.",
}


class NotificacaoService:
    """
    Cria as notificações da aplicação a partir dos eventos das denúncias.
    Best-effort: uma falha a notificar nunca pode desfazer nem impedir a
    acção principal (criar denúncia, mudar estado, designar agente).
    """

    # ---- base -----------------------------------------------------------

    @staticmethod
    def notificar(utilizadores, tipo, titulo, mensagem, denuncia=None):
        try:
            Notificacao.objects.bulk_create([
                Notificacao(
                    utilizador=u,
                    tipo=tipo,
                    titulo=titulo[:150],
                    mensagem=mensagem[:500],
                    denuncia=denuncia,
                )
                for u in utilizadores
            ])
        except Exception:
            logger.exception("Falha ao criar notificações (%s)", tipo)

    @staticmethod
    def _tipo(denuncia):
        return TIPO_LABEL.get(denuncia.tipo_infracao, "infração")

    # ---- eventos ---------------------------------------------------------

    @staticmethod
    def denuncia_criada(denuncia):
        """Cidadão: confirmação. Acidente: Admin do posto da zona (ou os
        Super Admins, se o ponto não cair em nenhuma jurisdição - alguém
        tem de saber que ficou sem posto)."""
        eh_acidente = denuncia.tipo_infracao == Denuncia.tipoInfracao.ACIDENTE
        principal_id = denuncia.denuncia_principal_id

        if principal_id and eh_acidente:
            detalhe = ("Este acidente já tinha sido reportado por outra pessoa; o seu reporte foi juntado ao existente"
                       + (" e já vai um agente a caminho." if denuncia.estado == Denuncia.Estado.EM_ATENDIMENTO else "."))
        elif principal_id:
            detalhe = ("Outro cidadão já tinha denunciado esta infração; a sua denúncia foi ligada à dele como "
                       "testemunha e reforça o processo. O vídeo vai ser analisado automaticamente.")
        elif eh_acidente and denuncia.admin_responsavel_id:
            detalhe = "Foi enviada ao posto policial responsável pela zona."
        elif eh_acidente:
            detalhe = "O local não pertence a nenhuma jurisdição registada; foi comunicada à administração do sistema."
        else:
            detalhe = "O vídeo vai ser analisado automaticamente."

        NotificacaoService.notificar(
            [denuncia.cidadao.utilizador],
            Notificacao.Tipo.DENUNCIA_RECEBIDA,
            f"Denúncia #{denuncia.id} recebida",
            f"A sua denúncia de {NotificacaoService._tipo(denuncia)} foi registada. {detalhe}",
            denuncia,
        )

        if not eh_acidente:
            return

        local = denuncia.localizacao or "local não especificado"

        if principal_id:
            # Mesmo acidente: quem já foi avisado do primeiro reporte sabe
            # que chegou mais um (sem novo SMS).
            destinatarios = (
                [denuncia.admin_responsavel.utilizador] if denuncia.admin_responsavel_id
                else Utilizador.objects.filter(role=Utilizador.Role.SUPER_ADMIN, is_active=True)
            )
            NotificacaoService.notificar(
                destinatarios,
                Notificacao.Tipo.ACIDENTE_REPORTADO,
                f"Novo reporte do acidente #{principal_id}",
                f"Outra pessoa reportou o mesmo acidente em {local}.",
                denuncia.denuncia_principal,
            )
            return

        if denuncia.admin_responsavel_id:
            destinatarios = [denuncia.admin_responsavel.utilizador]
            mensagem = f"Nova denúncia de acidente de viação em {local}. Designe um agente para o local."
        else:
            destinatarios = Utilizador.objects.filter(role=Utilizador.Role.SUPER_ADMIN, is_active=True)
            mensagem = f"Acidente de viação em {local} fora de qualquer jurisdição registada - nenhum posto foi avisado."

        NotificacaoService.notificar(
            destinatarios,
            Notificacao.Tipo.ACIDENTE_REPORTADO,
            f"Acidente de viação #{denuncia.id}",
            mensagem,
            denuncia,
        )

    @staticmethod
    def estado_alterado(denuncia, origem=None, detalhe=None):
        """Cidadão: sempre que a sua denúncia muda de estado. `origem`
        ("IA"/"PT") afina a mensagem; `detalhe` acrescenta o motivo/código
        legal escrito pelo agente."""
        mensagem = (
            MENSAGEM_ESTADO_CIDADAO.get((denuncia.estado, origem))
            or MENSAGEM_ESTADO_CIDADAO.get(denuncia.estado)
        )
        if not mensagem:
            return

        if detalhe:
            mensagem = f"{mensagem} {detalhe}"

        NotificacaoService.notificar(
            [denuncia.cidadao.utilizador],
            Notificacao.Tipo.ESTADO_ALTERADO,
            f"Denúncia #{denuncia.id}: {denuncia.get_estado_display()}",
            mensagem,
            denuncia,
        )

    @staticmethod
    def nova_para_revisao(denuncia):
        """Agentes: a denúncia entrou na fila de revisão (a análise
        automática confirmou a infração). Os agentes do posto da zona;
        sem posto, todos - é a mesma regra da fila `pt/validadas`."""
        pts = PT.objects.select_related("utilizador").filter(utilizador__is_active=True)
        if denuncia.admin_responsavel_id:
            pts = pts.filter(admin_id=denuncia.admin_responsavel_id)

        NotificacaoService.notificar(
            [p.utilizador for p in pts],
            Notificacao.Tipo.NOVA_PARA_REVISAO,
            f"Nova denúncia #{denuncia.id} para revisão",
            f"Denúncia de {NotificacaoService._tipo(denuncia)} em {denuncia.localizacao or 'local não especificado'} aguarda a sua decisão.",
            denuncia,
        )

    @staticmethod
    def analise_falhou(denuncia):
        """Cidadão: o vídeo não pôde ser analisado (todas as tentativas
        falharam) - sem isto a denúncia ficava pendente sem explicação."""
        NotificacaoService.notificar(
            [denuncia.cidadao.utilizador],
            Notificacao.Tipo.ANALISE_FALHOU,
            f"Denúncia #{denuncia.id}: não foi possível analisar o vídeo",
            "O vídeo não pôde ser analisado automaticamente (ficheiro danificado ou ilegível). "
            "Se possível, crie uma nova denúncia com outro vídeo.",
            denuncia,
        )

    @staticmethod
    def agente_designado(denuncia):
        """Agente: o Admin designou-o para um acidente. Cidadão: estado."""
        if denuncia.pt_id:
            NotificacaoService.notificar(
                [denuncia.pt.utilizador],
                Notificacao.Tipo.AGENTE_DESIGNADO,
                f"Designado para o acidente #{denuncia.id}",
                f"Dirija-se ao local: {denuncia.localizacao or 'local não especificado'}.",
                denuncia,
            )
        NotificacaoService.estado_alterado(denuncia)

    # ---- consulta --------------------------------------------------------

    @staticmethod
    def listar(utilizador, so_nao_lidas=False):
        qs = Notificacao.objects.filter(utilizador=utilizador)
        if so_nao_lidas:
            qs = qs.filter(lida=False)
        return qs

    @staticmethod
    def contar_nao_lidas(utilizador):
        return Notificacao.objects.filter(utilizador=utilizador, lida=False).count()

    @staticmethod
    def marcar_lida(notificacao_id, utilizador):
        # Filtra pelo utilizador: ninguém marca notificações de outro.
        return Notificacao.objects.filter(id=notificacao_id, utilizador=utilizador).update(lida=True)

    @staticmethod
    def marcar_todas_lidas(utilizador):
        return Notificacao.objects.filter(utilizador=utilizador, lida=False).update(lida=True)
