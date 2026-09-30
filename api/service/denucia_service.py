from django.utils import timezone
from django.db.models import Q

from api.model.user import Utilizador, Cidadao, PT
from api.model.denuncia import Denuncia
from .resultado_analise_service import ResultadoAnaliseService
from .jurisdicao_service import JurisdicaoService
from .notificacao_service import NotificacaoService
from .duplicados_service import DuplicadosService
# @kenny dasilva
# Servico de gestao de denuncia (denuncia)
# Responsabilidades: 
# 1. Criar denuncia
# 2. Listar denuncia
# 3. Obter detalhes de um denuncia
# 4. Actualizar detalhes de um denuncia
# 5. Apagar um denuncia

class DenunciaService:

    @staticmethod
    def listar_denuncias():
        return Denuncia.objects.all()
    
    @staticmethod
    def listar_denuncias_validadas(admin_id=None):
        """
        Fila de denúncias validadas para um PT decidir. Quando `admin_id` é
        dado (posto do PT autenticado), fica restrita às denúncias da
        jurisdição desse posto - mais as que não têm nenhum posto
        determinado (`admin_responsavel` vazio), que ficam visíveis a
        todos os PT como rede de segurança enquanto a cobertura de
        jurisdições (vias/bairros por posto) ainda não é total.
        """
        # Relacionada cuja principal já está na fila: o grupo aparece uma
        # só vez (na principal, com "+N testemunhas").
        # Excepção: localização contraditória (provável falsa) aparece
        # sempre, para o agente a decidir explicitamente.
        qs = Denuncia.objects.filter(estado="VALIDADA").exclude(
            denuncia_principal__estado=Denuncia.Estado.VALIDADA,
            localizacao_contraditoria=False,
        )

        if admin_id is not None:
            qs = qs.filter(Q(admin_responsavel_id=admin_id) | Q(admin_responsavel__isnull=True))

        return qs

    @staticmethod
    def obter_denuncia_por_id(denuncia_id):
        try:
            return Denuncia.objects.get(id=denuncia_id)
        except Denuncia.DoesNotExist:
            return None

    

    @staticmethod
    def criar_denuncia(
        cidadao_id,
        matricula,
        descricao,
        tipo_infracao,
        localizacao,
        sentido_direccao,
        latitude=None,
        longitude=None
    ):
        cidadao = DenunciaService.encontrar_utilizador_cidadao(cidadao_id)

        # Determina o posto responsável pela zona da denúncia, para todos os
        # tipos (antes só Acidente) - encaminha automaticamente aos agentes
        # do posto certo. Sem lat/lng, ou fora de qualquer jurisdição
        # conhecida, fica sem posto (None) e cai na fila global de PT.
        admin_responsavel = JurisdicaoService.encontrar_admin_por_localizacao(latitude, longitude)

        # Acidente não tem análise de vídeo: com posto encontrado, fica logo
        # "encaminhada" ao Admin (que recebe o SMS). Sem posto na zona fica
        # PENDENTE - ninguém foi avisado, não seria verdade dizer o contrário.
        estado = Denuncia.Estado.PENDENTE
        if tipo_infracao == Denuncia.tipoInfracao.ACIDENTE and admin_responsavel:
            estado = Denuncia.Estado.ENCAMINHADA

        # Mesma infração/acidente já denunciado por outro cidadão: liga à
        # primeira. Um acidente junta-se ao existente e herda o posto, o
        # estado e o agente já designado.
        principal = DuplicadosService.encontrar_principal(
            cidadao.id, tipo_infracao, matricula, latitude, longitude
        )
        pt = None
        if principal and tipo_infracao == Denuncia.tipoInfracao.ACIDENTE:
            admin_responsavel = principal.admin_responsavel
            estado = principal.estado
            pt = principal.pt

        denuncia = Denuncia.objects.create(
            estado=estado,
            denuncia_principal=principal,
            pt=pt,
            cidadao=cidadao,
            matricula=matricula,
            descricao=descricao,
            tipo_infracao=tipo_infracao,
            localizacao=localizacao,
            sentido_direccao=sentido_direccao or "",
            latitude=latitude,
            longitude=longitude,
            descricao_pt="",
            codigo_legal="",
            admin_responsavel=admin_responsavel
        )

        cidadao.numero_denuncias += 1
        cidadao.save()

        NotificacaoService.denuncia_criada(denuncia)

        return denuncia

    @staticmethod
    def actualizar_estado(denuncia_id, estado):
        denuncia = Denuncia.objects.get(id=denuncia_id)
        estado_anterior = denuncia.estado
        denuncia.estado = estado
        denuncia.save()

        if denuncia.estado != estado_anterior:
            NotificacaoService.estado_alterado(denuncia)

        return denuncia


    @staticmethod
    def actualizar_estado_PT(denuncia_id, estado, codigo_legal, descricao_pt, pt_id):

        denuncia = Denuncia.objects.get(id=denuncia_id)
        analise=ResultadoAnaliseService.obter_por_denuncia(denuncia_id=denuncia.id)
        analise.codigo_legal=codigo_legal
        analise.descricao=descricao_pt
        analise.save()

        denuncia.pt = DenunciaService.encontrar_utilizador_PT(pt_id)
        estado_anterior = denuncia.estado
        denuncia.estado = estado
        if estado != estado_anterior:
            denuncia.decidido_em = timezone.now()

        denuncia.save()

        if denuncia.estado != estado_anterior:
            partes = []
            if descricao_pt:
                partes.append(f"Nota do agente: {descricao_pt.strip().rstrip('.')}.")
            if codigo_legal and estado == Denuncia.Estado.APROVADA:
                partes.append(f"Código legal aplicado: {codigo_legal.strip().rstrip('.')}.")
            NotificacaoService.estado_alterado(denuncia, origem="PT", detalhe=" ".join(partes) or None)

        # Aprovação vale para a infração: estende-se às outras denúncias
        # abertas do mesmo grupo (testemunhas). Rejeição não - pode ser só
        # este vídeo que não serve, as outras continuam na fila.
        if estado == Denuncia.Estado.APROVADA:
            raiz = denuncia.denuncia_principal or denuncia
            # Nunca aprova automaticamente uma de localização contraditória.
            grupo = Denuncia.objects.filter(
                Q(id=raiz.id) | Q(denuncia_principal_id=raiz.id),
                estado__in=[Denuncia.Estado.PENDENTE, Denuncia.Estado.VALIDADA],
                localizacao_contraditoria=False,
            ).exclude(id=denuncia.id)
            for outra in grupo:
                outra.pt = denuncia.pt
                outra.estado = Denuncia.Estado.APROVADA
                outra.decidido_em = denuncia.decidido_em
                outra.save()
                NotificacaoService.estado_alterado(outra, origem="PT")

        return denuncia

    

    @staticmethod
    def apagar_denuncia(denuncia_id):
        denuncia = Denuncia.objects.get(id=denuncia_id)
        denuncia.delete()

    @staticmethod
    def listar_por_cidadao(cidadao_id):
        cidadao = DenunciaService.encontrar_utilizador_cidadao(cidadao_id)
        return Denuncia.objects.filter(cidadao_id=cidadao.id)

    @staticmethod
    def listar_por_pt(pt_id):
        pt = DenunciaService.encontrar_utilizador_PT(pt_id)
        return Denuncia.objects.filter(pt_id=pt.id)

    @staticmethod
    def listar_acidentes_por_admin(admin_id):
        # Reportes do mesmo acidente aparecem juntos, na principal
        # ("N reportes"), não como acidentes separados.
        return Denuncia.objects.filter(
            admin_responsavel_id=admin_id,
            tipo_infracao=Denuncia.tipoInfracao.ACIDENTE,
            denuncia_principal__isnull=True
        )

    @staticmethod
    def designar_pt_acidente(denuncia_id, pt_id, admin_id):
        """
        O Admin do posto responsável escolhe qual agente vai ao local do
        acidente. Passa o estado a EM_ATENDIMENTO, para o cidadão ver que
        já vai um agente a caminho.

        Só aceita acidentes da jurisdição deste Admin e agentes do seu
        próprio posto (`pt_id` é o id do PT, não do utilizador).
        """
        denuncia = Denuncia.objects.get(
            id=denuncia_id,
            admin_responsavel_id=admin_id,
            tipo_infracao=Denuncia.tipoInfracao.ACIDENTE
        )

        try:
            pt = PT.objects.get(id=pt_id, admin_id=admin_id)
        except PT.DoesNotExist:
            raise ValueError("Agente não pertence a este posto")

        denuncia.pt = pt
        denuncia.estado = Denuncia.Estado.EM_ATENDIMENTO
        # Primeira designação conta para o tempo de resposta; trocar de
        # agente depois não o reinicia.
        denuncia.designado_em = denuncia.designado_em or timezone.now()
        denuncia.save()

        NotificacaoService.agente_designado(denuncia)

        # Os outros reportes do mesmo acidente seguem o principal - cada
        # cidadão que reportou sabe que vai um agente a caminho.
        for rel in denuncia.relacionadas.filter(estado__in=[Denuncia.Estado.ENCAMINHADA, Denuncia.Estado.PENDENTE]):
            rel.pt = pt
            rel.estado = Denuncia.Estado.EM_ATENDIMENTO
            rel.designado_em = rel.designado_em or denuncia.designado_em
            rel.save()
            NotificacaoService.estado_alterado(rel)

        return denuncia

    @staticmethod  
    def encontrar_utilizador_cidadao(utilizador_id):
        try:
            cidadao = Cidadao.objects.get(utilizador_id=utilizador_id)
            return cidadao
        except Cidadao.DoesNotExist: 
            raise ValueError(
                f"Nenhum cidadao encontrado para o utilizador_id {utilizador_id}"
            )

    @staticmethod  
    def encontrar_utilizador_PT(utilizador_id):
        try:
            pt = PT.objects.get(utilizador_id=utilizador_id)
            return pt
        except PT.DoesNotExist:  
            raise ValueError(
                f"Nenhum PT encontrado para o utilizador_id {utilizador_id}"
            )