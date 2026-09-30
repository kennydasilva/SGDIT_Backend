from django.http import HttpResponse
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.permissions.role_permissions import IsAdminOrSuperAdmin
from api.service.relatorio_exportacao import gerar_excel, gerar_pdf
from api.service.relatorio_service import RelatorioService

FILTROS = [
    openapi.Parameter("data_inicio", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="AAAA-MM-DD"),
    openapi.Parameter("data_fim", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="AAAA-MM-DD"),
    openapi.Parameter("admin_id", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                      description="Id do posto (Admin), ou 'sem_posto'. Só Super Admin; o Admin vê sempre o seu."),
    openapi.Parameter("tipo", openapi.IN_QUERY, type=openapi.TYPE_STRING),
    openapi.Parameter("estado", openapi.IN_QUERY, type=openapi.TYPE_STRING),
]


class RelatorioViewSet(ViewSet):
    """
    Relatórios para o Super Admin (tudo, com filtro de posto) e para o
    Admin (sempre só o seu posto - lido do utilizador autenticado, nunca
    do pedido, para um Admin não ver outro posto).
    """

    permission_classes = [IsAdminOrSuperAdmin]

    def _filtros(self, request):
        admin_forcado = None
        if request.user.role == "ADMIN":
            admin = getattr(request.user, "admin", None)
            admin_forcado = admin.id if admin else -1  # sem posto associado: nada
        return RelatorioService.ler_filtros(request.query_params, admin_forcado)

    def _nome_ficheiro(self, extensao):
        return f"relatorio-sgdit-{timezone.localtime().strftime('%Y%m%d-%H%M')}.{extensao}"

    @swagger_auto_schema(operation_description="Resumo com filtros", manual_parameters=FILTROS)
    @action(detail=False, methods=["get"], url_path="resumo")
    def resumo(self, request):
        return Response(RelatorioService.obter_resumo(self._filtros(request)))

    @swagger_auto_schema(operation_description="Exportar em Excel (Resumo + lista de denúncias)", manual_parameters=FILTROS)
    @action(detail=False, methods=["get"], url_path="exportar/excel")
    def exportar_excel(self, request):
        resposta = HttpResponse(
            gerar_excel(self._filtros(request)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resposta["Content-Disposition"] = f'attachment; filename="{self._nome_ficheiro("xlsx")}"'
        return resposta

    @swagger_auto_schema(operation_description="Exportar em PDF (Resumo + lista de denúncias)", manual_parameters=FILTROS)
    @action(detail=False, methods=["get"], url_path="exportar/pdf")
    def exportar_pdf(self, request):
        resposta = HttpResponse(gerar_pdf(self._filtros(request)), content_type="application/pdf")
        resposta["Content-Disposition"] = f'attachment; filename="{self._nome_ficheiro("pdf")}"'
        return resposta
