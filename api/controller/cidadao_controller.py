from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.service.cidadao_service import CidadaoService
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


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