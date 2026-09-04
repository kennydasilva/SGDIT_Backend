from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema

from api.permissions.role_permissions import IsSuperAdmin
from api.service.cidadao_service import CidadaoService
from api.pagination import PaginacaoPadrao

CAMPOS_ORDENACAO_CIDADAOS = {
    "id": "id",
    "numero_denuncias": "numero_denuncias",
    "data_registo": "utilizador__data_registo",
}


class SuperAdminViewSet(ViewSet):

    permission_classes = [IsSuperAdmin]
    pagination_class = PaginacaoPadrao

    @swagger_auto_schema(
        operation_description="Listar todos os cidadãos (paginado; ?page=&page_size=&ordering=)"
    )
    @action(detail=False, methods=["get"], url_path="cidadao/lista")
    def listar_cidadaos(self, request):

        ordering = request.query_params.get("ordering", "-utilizador__data_registo")
        campo = ordering.lstrip("-")
        campo_real = CAMPOS_ORDENACAO_CIDADAOS.get(campo)

        if not campo_real:
            ordering = "-utilizador__data_registo"
        else:
            ordering = f"-{campo_real}" if ordering.startswith("-") else campo_real

        cidadaos = CidadaoService.listar_cidadaos().select_related("utilizador").order_by(ordering)

        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(cidadaos, request, view=self)

        data = [
            {
                "id": c.id,
                "nome": c.utilizador.nome,
                "email": c.utilizador.email,
                "data_registo": c.utilizador.data_registo,
                "numero": c.utilizador.numero,
                "numero_denuncias": c.numero_denuncias,
                "ativo": c.utilizador.is_active,
            }
            for c in pagina
        ]

        return paginator.get_paginated_response(data)

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
