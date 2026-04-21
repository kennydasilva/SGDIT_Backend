from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.service.cidadao_service import CidadaoService
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.viewsets import ViewSet
from api.permissions.role_permissions import IsCidadao


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

        cidadao=CidadaoService.registar_cidadao(
            nome,
            email,
            password
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

        cidadao = CidadaoService.obter_cidadao(pk)

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
            
        }

        return Response(data)