import os
from api.model import denuncia
from api.model.analise import ResultadoAnalise
from api.model.denuncia import Denuncia


class ResultadoAnaliseService:

    @staticmethod
    def executar_analise(denuncia, output_path, alertas):

        if ResultadoAnalise.objects.filter(denuncia=denuncia).exists():
            print("Já processado, ignorando...")
            return ResultadoAnalise.objects.get(denuncia=denuncia)

        relative_path = os.path.relpath(output_path, "media")

        resultado, created = ResultadoAnalise.objects.update_or_create(
            denuncia=denuncia,
            defaults={
                "caminho_ficheiro_processado": relative_path,
                "descricao": f"Analise automatica para {denuncia.tipo_infracao}",
                "codigo_legal": denuncia.codigo_legal,
                "confianca": 0.85,
                "infracao_detectada": True,
                
            }
        )

        if alertas > 0 :
            denuncia.estado = "VALIDADA"
        else :
            denuncia.estado = "REJEITADA"

        denuncia.save()

        return resultado

    @staticmethod
    def obter_por_denuncia(denuncia_id):
        try:
            return ResultadoAnalise.objects.get(denuncia_id=denuncia_id)
        except ResultadoAnalise.DoesNotExist:
            return None





