from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from api.service.notificacao_service import NotificacaoService
from api.helper.dataConvertion import formatar_data
from api.pagination import PaginacaoPadrao


class NotificacaoViewSet(ViewSet):
    """
    Notificações do utilizador autenticado - qualquer papel. Nunca aceita
    um id de utilizador no pedido: cada um só vê e marca as suas.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = PaginacaoPadrao

    @swagger_auto_schema(
        operation_description="Listar as minhas notificações, mais recentes primeiro "
                               "(paginado; ?page=&page_size=&nao_lidas=1)"
    )
    def list(self, request):
        so_nao_lidas = request.query_params.get("nao_lidas") in ("1", "true")
        qs = NotificacaoService.listar(request.user, so_nao_lidas)

        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(qs, request, view=self)

        data = [
            {
                "id": n.id,
                "tipo": n.tipo,
                "titulo": n.titulo,
                "mensagem": n.mensagem,
                "denuncia_id": n.denuncia_id,
                "lida": n.lida,
                "criada_em": formatar_data(n.criada_em),
            }
            for n in pagina
        ]
        return paginator.get_paginated_response(data)

    @swagger_auto_schema(operation_description="Número de notificações por ler")
    @action(detail=False, methods=["get"], url_path="contagem")
    def contagem(self, request):
        return Response({"nao_lidas": NotificacaoService.contar_nao_lidas(request.user)})

    @swagger_auto_schema(operation_description="Marcar uma notificação como lida")
    @action(detail=True, methods=["patch"], url_path="lida")
    def marcar_lida(self, request, pk=None):
        if not NotificacaoService.marcar_lida(pk, request.user):
            return Response({"error": "Notificação não encontrada"}, status=404)
        return Response({"message": "Notificação marcada como lida"})

    @swagger_auto_schema(operation_description="Marcar todas as minhas notificações como lidas")
    @action(detail=False, methods=["patch"], url_path="marcar-todas-lidas")
    def marcar_todas_lidas(self, request):
        total = NotificacaoService.marcar_todas_lidas(request.user)
        return Response({"message": "Notificações marcadas como lidas", "total": total})
