from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from api.permissions.role_permissions import IsAdmin, IsPT, IsAdminOrSuperAdmin
from api.service.pt_service import PTService
from api.serializers.user_serializer import PTCreateSerializer, PTResponseSerializer
from api.pagination import PaginacaoPadrao
from rest_framework.decorators import action

def _serializar_pts(pts):
    return [
        {
            "id": p.id,
            "nome": p.utilizador.nome,
            "email": p.utilizador.email,
            "numero_agente": p.numero_agente,
            "localizacao": p.localizacao,
            "admin_id": p.admin_id
        }
        for p in pts
    ]


class PtViewSet(ViewSet):

    permission_classes = [IsAdmin]
    pagination_class = PaginacaoPadrao

    def get_permissions(self):
        if self.action == "list":
            return [IsAdminOrSuperAdmin()]
        return [IsAdmin()]

    @swagger_auto_schema(
        operation_description="Listar todos os PTs (paginado; ?page=&page_size=)",
        responses={200: PTResponseSerializer(many=True)}
    )
    def list(self, request):
        pts = PTService.listar_pts().select_related("utilizador").order_by("id")

        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(pts, request, view=self)

        return paginator.get_paginated_response(_serializar_pts(pagina))

    



    @swagger_auto_schema(
        operation_description="Criar PT",
        request_body=PTCreateSerializer
    )
    def create(self, request):

        pt = PTService.criar_pt(
            request.data.get("nome"),
            request.data.get("email"),
            request.data.get("password"),
            request.data.get("numero_agente"),
            request.data.get("localizacao"),
            request.data.get("admin_id"),
        )

        return Response(
            {"message": "PT criado", "id": pt.id},
            status=status.HTTP_201_CREATED
        )



    @swagger_auto_schema(
        operation_description="Actualizar dados do PT",
        request_body=PTCreateSerializer,
        responses={
            200: "PT actualizado com sucesso",
            404: "PT nao encontrado"
        }
    )
    def update(self, request, pk=None):

        PTService.actualizar_pt(
            pk,
            request.data.get("nome"),
            request.data.get("numero_agente"),
            request.data.get("localizacao"),
        )

        return Response({"message": "PT actualizado"})
    



    @swagger_auto_schema(
        operation_description="Apagar um PT pelo ID",
        responses={
            204: "PT apagado com sucesso",
            404: "PT nao encontrado",
            403: "Sem permissao"
        }
    )
    def destroy(self, request, pk=None):

        PTService.apagar_pt(pk)

        return Response(status=status.HTTP_204_NO_CONTENT)



    
    @swagger_auto_schema(
        operation_description="Listar todos os PTs de um admin especifico (paginado; ?page=&page_size=)",
        responses={200: PTResponseSerializer(many=True)}
    )
    @action(detail=False, methods=["get"], url_path="admin/(?P<admin_id>[^/.]+)")
    def listar_por_admin(self, request, admin_id=None):

        pts = PTService.listar_pts_por_admin(admin_id).select_related("utilizador").order_by("id")

        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(pts, request, view=self)

        return paginator.get_paginated_response(_serializar_pts(pagina))






class PtUserViewSet(ViewSet):

    permission_classes = [IsPT]

    @swagger_auto_schema(
        operation_description="Obter um PT por ID",
        responses={200: PTResponseSerializer}
    )
    def retrieve(self, request, pk=None):

        pt = PTService.obter_pt(pk)

        if not pt:
            return Response(
                {"error": "PT nao encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            "id": pt.id,
            "nome": pt.utilizador.nome,
            "email": pt.utilizador.email,
            "numero_agente": pt.numero_agente,
            "localizacao": pt.localizacao,
            "data_registo": pt.utilizador.data_registo,
            "numero": pt.utilizador.numero,
            "admin_id": pt.admin_id
        }

        return Response(data)








    