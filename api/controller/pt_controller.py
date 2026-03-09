#@kenny dasilva
#Controller para gestao de policias de transito (PTs)
#Responsabilidades: 
#1. Criar PTs
#2. Listar PTs
#3. Obter detalhes de um PT
#4. Actualizar detalhes de um PT
#5. Apagar um PT


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.permissions.role_permissions import IsAdmin
from api.service.admin_service import AdminService
from api.service.pt_service import PTService
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.serializers.user_serializer import CriarAdminSerializer, AdminResponseSerializer, PTSerializer

class PtController(APIView):
    
    permission_classes=[IsAdmin]

    @swagger_auto_schema(
            operation_description="Listar policiais de transito",
            responses={200: PTSerializer(many=True)}

    )
    def get(self, request):

        pts=PTService.listar_pts()

        data=[
            {
                "id":p.id,
                "nome":p.utilizador.nome,
                "email":p.utilizador.email,
                "numero_agente":p.numero_agente,
                "localizacao":p.localizacao,
                "admin_id":p.admin_id
            }
            for p in pts
        ]

        return Response(data)
    
    @swagger_auto_schema(
        operation_description="Criar policia de transito",
        request_body=PTSerializer,
        responses={201: PTSerializer}
    )
    def post(self, request):

        nome=request.data.get("nome")
        email=request.data.get("email")
        password=request.data.get("password")
        numero_agente=request.data.get("numero_agente")
        localizacao=request.data.get("localizacao")
        admin_id=request.data.get("admin_id")

        pt=PTService.criar_pt(
            nome,
            email,
            password,
            numero_agente,
            localizacao,
            admin_id
        )

        return Response({
            "message":"Policia de transito criado",
            "id":pt.id}
        )
    
    @swagger_auto_schema(
        operation_description="Actualizar detalhes de um Policia de Transito",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "pt_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "nome": openapi.Schema(type=openapi.TYPE_STRING),
                "numero_agente": openapi.Schema(type=openapi.TYPE_STRING),
                "localizacao": openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={200: "Policia de transito actualizado"}
    )
    def put(self, request):

        nome = request.data.get("nome")
        numero_agente=request.data.get("numero_agente")
        localizacao=request.data.get("localizacao")
        pt_id=request.data.get("pt_id")

        pt=PTService.actualizar_pt(
            pt_id,
            nome,
            numero_agente,
            localizacao
        )

        return Response(
            {"message":"Policia de transito actualizado"}
        )

    @swagger_auto_schema(
        operation_description="Apagar um policia de transito",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "pt_id": openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={204: "Policia de transito apagado"}
    )
    def delete(self, request):

        pt_id=request.data.get("pt_id")
        PTService.apagar_pt(pt_id)

        return Response(
            {"message":"Policia de transito apagado"},
            status=status.HTTP_204_NO_CONTENT
        )