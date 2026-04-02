from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action

from api.service.denucia_service import DenunciaService
from api.serializers.denuncia_serializer import (
    DenunciaCreateSerializer,
    DenunciaResponseSerializer
)

from api.Analise.Contramao import main_contramao
from api.Analise.parado import  main_parado
from api.Analise.velocidade import main_velocidade
from api.evidencia import Evidencia 


class DenunciaViewSet(ViewSet):

    @swagger_auto_schema(
        operation_description="Listar todas denuncias",
        responses={200: DenunciaResponseSerializer(many=True)}
    )
    def list(self, request):

        denuncias = DenunciaService.listar_denuncias()

        data = [
            {
                "id": d.id,
                "cidadao_id": d.cidadao_id,
                "pt_id": d.pt_id,
                "matricula": d.matricula,
                "estado": d.estado,
                "descricao": d.descricao,
                "codigo_legal": d.codigo_legal,
                "tipo_infracao": d.tipo_infracao,
                "localizacao": d.localizacao,
                "data_registo": d.data_registo,
            }
            for d in denuncias
        ]

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

        data = {
            "id": denuncia.id,
            "cidadao_id": denuncia.cidadao_id,
            "pt_id": denuncia.pt_id,
            "matricula": denuncia.matricula,
            "estado": denuncia.estado,
            "descricao": denuncia.descricao,
            "codigo_legal": denuncia.codigo_legal,
            "tipo_infracao": denuncia.tipo_infracao,
            "localizacao": denuncia.localizacao,
            "data_registo": denuncia.data_registo,
        }

        return Response(data)




    @swagger_auto_schema(
        operation_description="Criar denuncia",
        request_body=DenunciaCreateSerializer
    )
    def create(self, request):

        denuncia = DenunciaService.criar_denuncia(
            request.data.get("cidadao_id"),
            request.data.get("pt_id"),
            request.data.get("matricula"),
            request.data.get("descricao"),
            request.data.get("codigo_legal"),
            request.data.get("tipo_infracao"),
            request.data.get("localizacao"),
            request.data.get("sentido_direccao"),
        )

        try:
            ficheiro = request.FILES.get("caminho_ficheiro")
            if not ficheiro:
                return Response(
                    {"error": "Ficheiro de evidencia é obrigatório"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            evidencia = Evidencia.objects.create(
                denuncia=denuncia,
                caminho_ficheiro=ficheiro
            )

            if denuncia.tipo_infracao == "CONTRAMAO":
                output_path = main_contramao(evidencia.caminho_ficheiro.path, denuncia)

            elif denuncia.tipo_infracao == "PARADO":
                output_path = main_parado(evidencia.caminho_ficheiro.path, denuncia)

            elif denuncia.tipo_infracao == "VELOCIDADE":
                output_path = main_velocidade(evidencia.caminho_ficheiro.path, denuncia)

            return Response(
                {"message": "Denuncia criada", "id": denuncia.id},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"error": f"Erro ao salvar a denuncia: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


        

    @swagger_auto_schema(
        operation_description="Actualizar estado da denuncia"
    )
    @action(detail=True, methods=["patch"], url_path="estado")
    def actualizar_estado(self, request, pk=None):

        estado = request.data.get("estado")

        denuncia = DenunciaService.actualizar_estado(pk, estado)

        return Response({
            "message": "Estado actualizado",
            "estado": denuncia.estado
        })

    @swagger_auto_schema(
        operation_description="Apagar denuncia"
    )
    def destroy(self, request, pk=None):

        DenunciaService.apagar_denuncia(pk)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_description="Listar denuncias por cidadao"
    )
    @action(detail=False, methods=["get"], url_path="cidadao/(?P<cidadao_id>[^/.]+)")
    def por_cidadao(self, request, cidadao_id=None):

        denuncias = DenunciaService.listar_por_cidadao(cidadao_id)

        data = [
            {
                "id": d.id,
                "matricula": d.matricula,
                "estado": d.estado,
                "descricao": d.descricao,
            }
            for d in denuncias
        ]

        return Response(data)

    @swagger_auto_schema(
        operation_description="Listar denuncias por PT"
    )
    @action(detail=False, methods=["get"], url_path="pt/(?P<pt_id>[^/.]+)")
    def por_pt(self, request, pt_id=None):

        denuncias = DenunciaService.listar_por_pt(pt_id)

        data = [
            {
                "id": d.id,
                "matricula": d.matricula,
                "estado": d.estado,
                "descricao": d.descricao,
            }
            for d in denuncias
        ]

        return Response(data)