from celery import shared_task
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action

from api.model.denuncia import Denuncia
from api.service.denucia_service import DenunciaService
from api.serializers.denuncia_serializer import (
    DenunciaCreateSerializer,
    DenunciaResponseSerializer,
    DenunciaUpdateSerializer,
)

from api.Analise.Contramao import main_contramao
from api.Analise.parado import main_parado
from api.Analise.velocidade import main_velocidade
from api.service.evidencia_service import EvidenciaService
import threading
import traceback
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from api.service.resultado_analise_service import ResultadoAnaliseService
from api.tasks.analise_task import processar_analise_async
from api.helper.dataConvertion import formatar_data

class DenunciaViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_description="Listar todas denuncias",
        responses={200: "sucesso na requisicao"}
    )
    def list(self, request):

        denuncias = DenunciaService.listar_denuncias()
        

        
        data = []

        for d in denuncias:

            resultadoAnalise = ResultadoAnaliseService.obter_por_denuncia(d.id)
            evidencia = EvidenciaService.obter_evidencia(d.id)

            ficheiro_processado = (
                resultadoAnalise.caminho_ficheiro_processado.url
                if resultadoAnalise and resultadoAnalise.caminho_ficheiro_processado
                else None
            )

            ficheiro_original = (
                evidencia.caminho_ficheiro.url
                if evidencia and evidencia.caminho_ficheiro
                else None
            )


            data_captura_formatada = formatar_data(evidencia.data_captura) if evidencia else None
            data_analise_formatada = formatar_data(resultadoAnalise.data_analise) if resultadoAnalise else None

            data.append(DenunciaViewSet.preparar_denuncia(d, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada))


        return Response(data)


        
        




    @swagger_auto_schema(
        operation_description="Obter denuncia por ID",
        responses={200: DenunciaResponseSerializer}
    )
    def retrieve(self, request, pk=None):

        denuncia = DenunciaService.obter_denuncia_por_id(pk)

        if not denuncia:
            return Response(
                {"error": "Denuncia nao encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )       

        resultadoAnalise = ResultadoAnaliseService.obter_por_denuncia(denuncia.id)
        evidencia = EvidenciaService.obter_evidencia(denuncia.id)

        ficheiro_processado = (
                resultadoAnalise.caminho_ficheiro_processado.url
                if resultadoAnalise and resultadoAnalise.caminho_ficheiro_processado
                else None
        )

        ficheiro_original = (
                evidencia.caminho_ficheiro.url
                if evidencia and evidencia.caminho_ficheiro
                else None
        )


        data_captura_formatada = formatar_data(evidencia.data_captura) if evidencia else None
        data_analise_formatada = formatar_data(resultadoAnalise.data_analise) if resultadoAnalise else None

        data= DenunciaViewSet.preparar_denuncia(denuncia, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada)

        return Response(data)



    

  



    @swagger_auto_schema(
        operation_description="Criar denuncia",
        request_body=DenunciaCreateSerializer,
        consumes=['multipart/form-data'] 
    )
    def create(self, request):
        from rest_framework.parsers import MultiPartParser, FormParser
        from django.conf import settings

        try:

            sentido_direccao = request.data.get("sentido_direccao")

            ficheiro = request.FILES.get("caminho_ficheiro")

            if not ficheiro:
                return Response({"error": "Ficheiro não enviado"}, status=400)

            if not ficheiro.name.endswith(('.mp4', '.avi', '.mov')):
                return Response({"error": "Formato inválido"}, status=400)

            max_size_mb = getattr(settings, "DENUNCIA_VIDEO_MAX_SIZE_MB", 100)
            if ficheiro.size > max_size_mb * 1024 * 1024:
                return Response(
                    {"error": f"Vídeo demasiado grande (máximo {max_size_mb}MB). Reduza a duração ou a qualidade do vídeo."},
                    status=400
                )

            denuncia = DenunciaService.criar_denuncia(
                request.data.get("cidadao_id"),
                request.data.get("matricula"),
                request.data.get("descricao"),
                request.data.get("tipo_infracao"),
                request.data.get("localizacao"),
                request.data.get("sentido_direccao")
            )

            evidencia = EvidenciaService.criar_evidencia(denuncia, ficheiro)

            
            processar_analise_async.apply_async(
                args=[
                    denuncia.tipo_infracao,
                    evidencia.caminho_ficheiro.path,
                    denuncia.id,
                    sentido_direccao
                ],
                countdown=5
            )

            return Response(
                {"message": "Denuncia criada com sucesso", "id": denuncia.id},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


        

    @swagger_auto_schema(
        operation_description="Actualizar estado da denuncia user PT",
        request_body=DenunciaUpdateSerializer
    )
    @action(detail=False, methods=["patch"], url_path="pt/actualizar", 
     parser_classes=[JSONParser, MultiPartParser])
    def actualizar_estado(self, request, data=None):

        denuncia_id = int(request.data.get("denuncia_id"))
        estado = request.data.get("estado")
        codigo_legal = request.data.get("codigo_legal")
        descricao_pt = request.data.get("descricao_pt")
        pt_id = int(request.data.get("pt_id"))

       

        denuncia = DenunciaService.actualizar_estado_PT(denuncia_id, estado, codigo_legal, descricao_pt, pt_id)

        return Response(denuncia.id, status=status.HTTP_200_OK)





    @swagger_auto_schema(
        operation_description="Apagar denuncia"
    )
    def destroy(self, request, pk=None):

        denuncia=DenunciaService.obter_denuncia_por_id(pk)
        evidencia=EvidenciaService.obter_evidencia(denuncia.id)
        
        resultadoAnalise=ResultadoAnaliseService.obter_por_denuncia(denuncia.id)

        if evidencia is not None:
            evidencia.delete()

        if resultadoAnalise is not None:
            resultadoAnalise.delete()

        DenunciaService.apagar_denuncia(pk)

        return Response(status=status.HTTP_204_NO_CONTENT)

        

    @swagger_auto_schema(
        operation_description="Listar denuncias por cidadao"
    )
    @action(detail=False, methods=["get"], url_path="cidadao/(?P<cidadao_id>[^/.]+)")
    def por_cidadao(self, request, cidadao_id=None):

        denuncias = DenunciaService.listar_por_cidadao(cidadao_id)
        

        
        data = []

        for d in denuncias:

            resultadoAnalise = ResultadoAnaliseService.obter_por_denuncia(d.id)
            evidencia = EvidenciaService.obter_evidencia(d.id)

            ficheiro_processado = (
                resultadoAnalise.caminho_ficheiro_processado.url
                if resultadoAnalise and resultadoAnalise.caminho_ficheiro_processado
                else None
            )

            ficheiro_original = (
                evidencia.caminho_ficheiro.url
                if evidencia and evidencia.caminho_ficheiro
                else None
            )


            data_captura_formatada = formatar_data(evidencia.data_captura) if evidencia else None
            data_analise_formatada = formatar_data(resultadoAnalise.data_analise) if resultadoAnalise else None

            data.append(DenunciaViewSet.preparar_denuncia(d, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada))

        return Response(data)

    

    @swagger_auto_schema(
        operation_description="Listar denuncias validadas"
    )
    @action(detail=False, methods=["get"], url_path="pt/validadas")
    def por_validadas(self, request):

        denuncias = DenunciaService.listar_denuncias_validadas()

        
        data = []

        for d in denuncias:

            
                resultadoAnalise = ResultadoAnaliseService.obter_por_denuncia(d.id)
                evidencia = EvidenciaService.obter_evidencia(d.id)

                ficheiro_processado = (
                    resultadoAnalise.caminho_ficheiro_processado.url
                    if resultadoAnalise and resultadoAnalise.caminho_ficheiro_processado
                    else None
                )

                ficheiro_original = (
                    evidencia.caminho_ficheiro.url
                    if evidencia and evidencia.caminho_ficheiro
                    else None
                )


                data_captura_formatada = formatar_data(evidencia.data_captura) if evidencia else None
                data_analise_formatada = formatar_data(resultadoAnalise.data_analise) if resultadoAnalise else None

                data.append(DenunciaViewSet.preparar_denuncia(d, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada))
                
            
        return Response(data)



    @swagger_auto_schema(
        operation_description="Listar denuncias por PT"
    )
    @action(detail=False, methods=["get"], url_path="pt/denuncias/(?P<pt_id>[^/.]+)")
    def por_pt(self, request, pt_id=None):

        denuncias = DenunciaService.listar_por_pt(pt_id)
        
        data = []

        for d in denuncias:

            resultadoAnalise = ResultadoAnaliseService.obter_por_denuncia(d.id)
            evidencia = EvidenciaService.obter_evidencia(d.id)

            ficheiro_processado = (
                resultadoAnalise.caminho_ficheiro_processado.url
                if resultadoAnalise and resultadoAnalise.caminho_ficheiro_processado
                else None
            )

            ficheiro_original = (
                evidencia.caminho_ficheiro.url
                if evidencia and evidencia.caminho_ficheiro
                else None
            )


            data_captura_formatada = formatar_data(evidencia.data_captura) if evidencia else None
            data_analise_formatada = formatar_data(resultadoAnalise.data_analise) if resultadoAnalise else None

            data.append(DenunciaViewSet.preparar_denuncia(d, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada))

        return Response(data)




    def preparar_denuncia(denuncia, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada):
        data={
                "id": denuncia.id,
                "matricula": denuncia.matricula,
                "estado": denuncia.estado,
                "descricao": denuncia.descricao,
                "tipo_infracao": denuncia.tipo_infracao,
                "localizacao": denuncia.localizacao,
                "sentido_direccao": denuncia.sentido_direccao,
                "ficheiro_processado": ficheiro_processado,
                "ficheiro_original": ficheiro_original,
                "data_captura": data_captura_formatada,
                "codigo_legal": resultadoAnalise.codigo_legal if resultadoAnalise else None,
                "confianca": resultadoAnalise.confianca if resultadoAnalise else None,
                "data_analise": data_analise_formatada,
                "infracao_detectada": resultadoAnalise.infracao_detectada if resultadoAnalise else None,
        }

        return data