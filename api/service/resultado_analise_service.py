import os
from api.model import denuncia
from api.model.analise import ResultadoAnalise
from api.model.denuncia import Denuncia


class ResultadoAnaliseService:

    @staticmethod
    def executar_analise(denuncia, output_path, alertas, confianca=0.5):

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
                "confianca": round(min(max(confianca, 0), 1), 2),
                "infracao_detectada": True,

            }
        )

        resultado.infracao_detectada = alertas > 0
        resultado.save()

        # Já decidida por um agente antes de a análise terminar (ex:
        # aprovada junto com a denúncia principal do grupo): a análise
        # fica registada, mas não volta a mudar o estado nem a notificar.
        if denuncia.estado in (Denuncia.Estado.APROVADA, Denuncia.Estado.REJEITADA, Denuncia.Estado.ARQUIVADA):
            return resultado

        denuncia.estado = Denuncia.Estado.VALIDADA if alertas > 0 else Denuncia.Estado.REJEITADA
        denuncia.save()

        # Import local: denucia_service -> resultado_analise_service já
        # importa neste sentido, evitar ciclo ao carregar os módulos.
        from api.service.notificacao_service import NotificacaoService
        NotificacaoService.estado_alterado(denuncia, origem="IA")
        # Relacionada cuja principal já está na fila: o agente já foi
        # avisado pela principal, não repetir.
        principal_na_fila = (
            denuncia.denuncia_principal_id
            and denuncia.denuncia_principal.estado == Denuncia.Estado.VALIDADA
            and not denuncia.localizacao_contraditoria
        )
        if denuncia.estado == Denuncia.Estado.VALIDADA and not principal_na_fila:
            NotificacaoService.nova_para_revisao(denuncia)

        return resultado

    @staticmethod
    def obter_por_denuncia(denuncia_id):
        try:
            return ResultadoAnalise.objects.get(denuncia_id=denuncia_id)
        except ResultadoAnalise.DoesNotExist:
            return None





