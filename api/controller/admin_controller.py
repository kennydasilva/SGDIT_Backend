from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.permissions.role_permissions import IsSuperAdmin
from api.service.admin_service import AdminService
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class AdminController(APIView):
    
    permission_classes=[IsSuperAdmin]

    @swagger_auto_schema(operation_description="Listar administradores")
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
        operation_description="Criar administrador"
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
        operation_description="Actualizar detalhes de um administrador"
    )
    def put(self, request, admin_id):

        nome = request.data.get("nome")
        posto=request.data.get("posto")

        admin=AdminService.actualizar_admin(
            admin_id,
            nome,
            posto
        )

        return Response(
            {"message":"Admin actualizado"}
        )

    @swagger_auto_schema(
        operation_description="Apagar um administrador"
    )
    def delete(self, request, admin_id):

        AdminService.apagar_admin(admin_id)

        return Response(
            {"message":"Admin apagado"},
            status=status.HTTP_204_NO_CONTENT
        )