from api.model.user import Utilizador, Cidadao, PT
from api.model.denuncia import Denuncia
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
        sentido_direccao
    ):
        cidadao = DenunciaService.encontrar_utilizador_cidadao(cidadao_id)

        denuncia = Denuncia.objects.create(
            cidadao=cidadao,
            matricula=matricula,
            descricao=descricao,
            tipo_infracao=tipo_infracao,
            localizacao=localizacao,
            sentido_direccao=sentido_direccao or "",
            descricao_pt="",
            codigo_legal=""
        )

        return denuncia

    @staticmethod
    def actualizar_estado(denuncia_id, estado):
        denuncia = Denuncia.objects.get(id=denuncia_id)
        denuncia.estado = estado
        denuncia.save()
        return denuncia

    @staticmethod
    def actualizar_estado_PT(denuncia_id, estado, pt_id, descricao_pt):
        denuncia = Denuncia.objects.get(id=denuncia_id)
        
        pt = DenunciaService.encontrar_utilizador_PT(pt_id)
        if pt is not None:  
            denuncia.descricao_pt = descricao_pt
            denuncia.pt = pt
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