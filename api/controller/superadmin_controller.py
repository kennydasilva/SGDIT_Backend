from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema

from api.permissions.role_permissions import IsSuperAdmin
from api.service.cidadao_service import CidadaoService


class SuperAdminViewSet(ViewSet):

    permission_classes = [IsSuperAdmin]

    @swagger_auto_schema(
        operation_description="Listar todos os cidadãos"
    )
    @action(detail=False, methods=["get"], url_path="cidadao/lista")
    def listar_cidadaos(self, request):

        cidadaos = CidadaoService.listar_cidadaos()

        data = [
            {
                "id": c.id,
                "nome": c.utilizador.nome,
                "email": c.utilizador.email,
                "data_registo": c.utilizador.data_registo,
                "numero": c.utilizador.numero,
                "ativo": c.utilizador.is_active,
            }
            for c in cidadaos
        ]

        return Response(data)

    @swagger_auto_schema(
        operation_description="Ativar ou desativar um cidadão",
        request_body={},
    )
    @action(detail=False, methods=["patch"], url_path="cidadao/(?P<cidadao_id>[^/.]+)/status")
    def alterar_status_cidadao(self, request, cidadao_id=None):

        try:
            cidadao = CidadaoService.obter_cidadaoById(cidadao_id)
        except Exception:
            cidadao = None

        if not cidadao:
            return Response(
                {"error": "Cidadão não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        cidadao.utilizador.is_active = bool(request.data.get("ativo"))
        cidadao.utilizador.save()

        return Response({"message": "Estado do cidadão atualizado"})
