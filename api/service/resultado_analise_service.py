import os
from api.model.analise import ResultadoAnalise
from api.model.denuncia import Denuncia


from api.Analise.Contramao import main_contramao
from api.Analise.parado import  main_parado
from api.Analise.velocidade import main_velocidade


class ResultadoAnaliseService:

    @staticmethod
    def executar_analise(denuncia,output_path,alertas):

        resultado = ResultadoAnalise.objects.create(
            denuncia=denuncia,
            caminho_ficheiro_processado=output_path,
            descricao=f"Analise automatica para {denuncia.tipo_infracao}",
            codigo_legal=denuncia.codigo_legal,
            confianca=0.85,
            infracao_detectada=True
        )

        if alertas>0:
            denuncia.estado = "VALIDADA"
        else:
            denuncia.estado = "REJEITADA"
        denuncia.save()

        return resultado

    @staticmethod
    def obter_por_denuncia(denuncia_id):
        try:
            return ResultadoAnalise.objects.get(denuncia_id=denuncia_id)
        except ResultadoAnalise.DoesNotExist:
            return None





