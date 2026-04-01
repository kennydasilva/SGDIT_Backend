from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.permissions.role_permissions import IsSuperAdmin
from api.service.admin_service import AdminService
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.serializers.user_serializer import CriarAdminSerializer, AdminResponseSerializer

class AdminController(APIView):
    
    permission_classes=[IsSuperAdmin]

    @swagger_auto_schema(
            operation_description="Listar administradores",
            responses={200: AdminResponseSerializer(many=True)}

    )
    def get(self, request):

        admins=AdminService.listar_admins()

        data=[
            {
                "id":a.id,
                "nome":a.utilizador.nome,
                "email":a.utilizador.email,
                "posto":a.posto
            }
            for a in admins
        ]

        return Response(data)
    
    @swagger_auto_schema(
        operation_description="Criar administrador",
        request_body=CriarAdminSerializer,
        responses={201: AdminResponseSerializer}
    )
    def post(self, request):

        nome=request.data.get("nome")
        email=request.data.get("email")
        password=request.data.get("password")
        posto=request.data.get("posto")

        admin=AdminService.criar_admin(
            nome,
            email,
            password,
            posto
        )

        return Response({
            "message":"Admin criado",
            "id":admin.id}
        )
    
    @swagger_auto_schema(
        operation_description="Actualizar detalhes de um administrador",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "admin_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "nome": openapi.Schema(type=openapi.TYPE_STRING),
                "posto": openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={200: "Admin actualizado"}
    )
    def put(self, request):

        nome = request.data.get("nome")
        posto=request.data.get("posto")
        admin_id=request.data.get("admin_id")
        admin=AdminService.actualizar_admin(
            admin_id,
            nome,
            posto
        )

        return Response(
            {"message":"Admin actualizado"}
        )

    @swagger_auto_schema(
        operation_description="Apagar um administrador",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "admin_id": openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={204: "Admin apagado"}
    )
    def delete(self, request):

        admin_id=request.data.get("admin_id")
        AdminService.apagar_admin(admin_id)

        return Response(
            {"message":"Admin apagado"},
            status=status.HTTP_204_NO_CONTENT
        )



