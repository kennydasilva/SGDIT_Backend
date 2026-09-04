from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from api.service.cidadao_service import CidadaoService
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.viewsets import ViewSet
from api.permissions.role_permissions import IsCidadao
from api.serializers.user_serializer import CidadaoResponseSerializer
from api.helper.dataConvertion import gerar_codigo_cidadao


class RegistarCidadaoController(APIView):

    authentication_classes=[]
    permission_classes=[]

    @swagger_auto_schema(
        operation_description="Cadastro de cidadão",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "nome": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
            }
        )
    )

    def post(self, request):

        nome=request.data.get("nome")
        email=request.data.get("email")
        password=request.data.get("password")
        numero=request.data.get("numero")

        if not nome or not email or not password:
            return Response(
                {"error": "Nome, email e password são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from api.model.user import Utilizador

        if Utilizador.objects.filter(email=email).exists():
            return Response(
                {"error": "Já existe uma conta registada com este email"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cidadao=CidadaoService.registar_cidadao(
            nome,
            email,
            password,
            numero
        )

        return Response(
            {"message": "Cidadão criado", "id": cidadao.id},
            status=status.HTTP_201_CREATED
        )





class CidadaoUserViewSet(ViewSet):

    permission_classes = [IsCidadao]

    @swagger_auto_schema(
        operation_description="Obter um cidadão por ID",
        responses={200: CidadaoResponseSerializer}
    )
    def retrieve(self, request, pk=None):

        cidadao = CidadaoService.obter_cidadaoById(pk)

        if not cidadao:
            return Response(
                {"error": "Cidadão não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            "id": cidadao.id,
            "nome": cidadao.utilizador.nome,
            "email": cidadao.utilizador.email,
            "data_registo": cidadao.utilizador.data_registo,
            "numero": cidadao.utilizador.numero,
            "numero_denuncias": cidadao.numero_denuncias,
            "codigo_ranking": gerar_codigo_cidadao(cidadao.id),
        }

        return Response(data)


    @swagger_auto_schema(
        operation_description="Actualizar dados do PT",
        request_body=CidadaoResponseSerializer,
        responses={
            200: "PT actualizado com sucesso",
            404: "PT nao encontrado"
        }
    )
    def update(self, request, pk=None):

        CidadaoService.actualizar_cidadao(
            pk,
            request.data.get("nome"),
            request.data.get("numero"),
        )

        return Response({"message": "PT actualizado"})

    @swagger_auto_schema(
        operation_description="Ranking anónimo dos cidadãos mais ativos (por número de denúncias)"
    )
    @action(detail=False, methods=["get"], url_path="ranking")
    def ranking(self, request):

        cidadaos = CidadaoService.listar_ranking(10)

        data = [
            {
                "posicao": i + 1,
                "codigo": gerar_codigo_cidadao(c.id),
                "numero_denuncias": c.numero_denuncias,
            }
            for i, c in enumerate(cidadaos)
        ]

        return Response(data)
