from api.model.user import Utilizador, Cidadao, PT
from api.model.denuncia import Denuncia
from .resultado_analise_service import ResultadoAnaliseService
from .jurisdicao_service import JurisdicaoService
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
    def listar_denuncias_validadas():
        return Denuncia.objects.filter(estado="VALIDADA")

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

        admin_responsavel = None
        if tipo_infracao == Denuncia.tipoInfracao.ACIDENTE:
            admin_responsavel = JurisdicaoService.encontrar_admin_por_localizacao(latitude, longitude)

        denuncia = Denuncia.objects.create(
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

        return denuncia

    @staticmethod
    def actualizar_estado(denuncia_id, estado):
        denuncia = Denuncia.objects.get(id=denuncia_id)
        denuncia.estado = estado
        denuncia.save()
        return denuncia


    @staticmethod
    def actualizar_estado_PT(denuncia_id, estado, codigo_legal, descricao_pt, pt_id):

        denuncia = Denuncia.objects.get(id=denuncia_id)
        analise=ResultadoAnaliseService.obter_por_denuncia(denuncia_id=denuncia.id)
        analise.codigo_legal=codigo_legal
        analise.descricao=descricao_pt
        analise.save()

        denuncia.pt = DenunciaService.encontrar_utilizador_PT(pt_id)
        denuncia.estado = estado

        denuncia.save()
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
        return Denuncia.objects.filter(
            admin_responsavel_id=admin_id,
            tipo_infracao=Denuncia.tipoInfracao.ACIDENTE
        )

    @staticmethod
    def designar_pt_acidente(denuncia_id, pt_id):
        """
        O Admin do posto responsável escolhe qual agente vai ao local do
        acidente. Só troca o PT atribuído - não mexe no `estado`, essa
        decisão (validar/rejeitar) continua a ser do próprio PT depois de
        atender a ocorrência.
        """
        denuncia = Denuncia.objects.get(id=denuncia_id)
        denuncia.pt = DenunciaService.encontrar_utilizador_PT(pt_id)
        denuncia.save()
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