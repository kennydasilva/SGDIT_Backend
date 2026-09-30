from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.permissions.role_permissions import IsSuperAdmin
from api.service.cidadao_service import CidadaoService
from api.service.configuracao_service import ConfiguracaoService
from api.service.jurisdicao_service import JurisdicaoService, ZonaSobrepostaError
from api.service.nominatim_service import NominatimService
from api.service.overpass_service import OverpassService
from api.pagination import PaginacaoPadrao


def _mascarar(valor):
    if not valor or len(valor) <= 4:
        return "••••"
    return "••••" + valor[-4:]

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

    # Listar (GET) ou criar/atualizar (POST) credenciais de integrações
    # externas (Google Maps, MozeSMS, etc.). Valores nunca são devolvidos
    # em claro - só mascarados.
    @action(detail=False, methods=["get", "post"], url_path="config")
    def config(self, request):

        if request.method == "POST":
            chave = request.data.get("chave")
            valor = request.data.get("valor")
            publica = bool(request.data.get("publica", False))
            descricao = request.data.get("descricao", "")

            if not chave or not valor:
                return Response(
                    {"error": "chave e valor são obrigatórios"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ConfiguracaoService.definir(chave, valor, publica, descricao)
            return Response({"message": "Configuração guardada"})

        configs = ConfiguracaoService.listar()

        data = [
            {
                "chave": c.chave,
                "publica": c.publica,
                "descricao": c.descricao,
                "valor_mascarado": _mascarar(c.get_valor()),
                "atualizado_em": c.atualizado_em,
            }
            for c in configs
        ]

        return Response(data)

    @swagger_auto_schema(
        operation_description="Apagar uma credencial de integração"
    )
    @action(detail=False, methods=["delete"], url_path="config/(?P<chave>[^/.]+)")
    def apagar_config(self, request, chave=None):
        ConfiguracaoService.apagar(chave)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_description="Pesquisar vias/estradas (OpenStreetMap Nominatim, filtrado a resultados do tipo via) "
                               "para atribuir à jurisdição de um posto. ?q=<pesquisa>"
    )
    @action(detail=False, methods=["get"], url_path="vias/pesquisar")
    def pesquisar_vias(self, request):
        query = request.query_params.get("q", "")
        return Response(NominatimService.pesquisar_vias(query))

    @swagger_auto_schema(
        operation_description="Pesquisar bairros/localidades (OpenStreetMap Nominatim), para depois listar as "
                               "vias desse bairro com 'vias/bairro/<osm_type>/<osm_id>/'. ?q=<pesquisa>"
    )
    @action(detail=False, methods=["get"], url_path="vias/pesquisar-bairro")
    def pesquisar_bairros(self, request):
        query = request.query_params.get("q", "")
        return Response(NominatimService.pesquisar_bairros(query))

    @swagger_auto_schema(
        operation_description="Listar todas as vias nomeadas dentro de um bairro (OpenStreetMap Overpass, "
                               "cacheado 1 dia) - para adicionar de uma vez à jurisdição de um posto"
    )
    @action(detail=False, methods=["get"], url_path="vias/bairro/(?P<osm_type>[^/.]+)/(?P<osm_id>[^/.]+)")
    def vias_do_bairro(self, request, osm_type=None, osm_id=None):
        vias = OverpassService.listar_vias_do_bairro(osm_type, osm_id)

        if vias is None:
            return Response(
                {"error": "Não foi possível obter as vias do bairro (serviço externo indisponível). Tenta novamente daqui a pouco."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(vias)

    @swagger_auto_schema(
        operation_description="Obter o contorno real (polígono, GeoJSON) de um bairro - para atribuir "
                               "como zona inteira à jurisdição de um posto, mais preciso que um rectângulo"
    )
    @action(detail=False, methods=["get"], url_path="vias/bairro/(?P<osm_type>[^/.]+)/(?P<osm_id>[^/.]+)/poligono")
    def poligono_do_bairro(self, request, osm_type=None, osm_id=None):
        poligono = NominatimService.obter_poligono_bairro(osm_type, osm_id)

        if poligono is None:
            return Response(
                {"error": "Não foi possível obter o contorno do bairro (serviço externo indisponível ou sem polígono). Tenta novamente daqui a pouco."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response({"polygon": poligono})

    # Vias/estradas atribuídas à jurisdição de um posto (Admin). Só o Super
    # Admin gere isto - protege o sistema de um Admin atribuir a si próprio
    # vias fora da sua jurisdição real.
    @action(detail=False, methods=["get", "post"], url_path="admin/(?P<admin_id>[^/.]+)/vias")
    def vias_jurisdicao(self, request, admin_id=None):

        if request.method == "POST":
            nome_via = request.data.get("nome_via")
            place_id = request.data.get("place_id")
            geometria = request.data.get("geometria")

            if not nome_via or not place_id:
                return Response(
                    {"error": "nome_via e place_id são obrigatórios"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Zona (polígono do bairro inteiro): recorta automaticamente
            # contra zonas já existentes de qualquer posto, para nunca
            # ficarem sobrepostas (igual ao TruckFreightEasy).
            if geometria and geometria.get("polygon"):
                try:
                    via = JurisdicaoService.adicionar_zona(admin_id, nome_via, place_id, geometria["polygon"])
                except ZonaSobrepostaError as erro:
                    return Response({"error": str(erro)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                via = JurisdicaoService.adicionar_via(admin_id, nome_via, place_id, geometria)

            return Response({"message": "Via adicionada à jurisdição", "id": via.id})

        vias = JurisdicaoService.listar_por_admin(admin_id)

        data = [
            {
                "id": v.id,
                "nome_via": v.nome_via,
                "place_id": v.place_id,
                "geometria": v.geometria,
            }
            for v in vias
        ]

        return Response(data)

    @swagger_auto_schema(
        operation_description="Adicionar várias vias de uma vez à jurisdição de um posto "
                               "(ex: todas as vias devolvidas por 'vias/bairro/...')",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "vias": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                ),
            }
        )
    )
    @action(detail=False, methods=["post"], url_path="admin/(?P<admin_id>[^/.]+)/vias-bulk")
    def vias_jurisdicao_bulk(self, request, admin_id=None):
        vias = request.data.get("vias") or []

        adicionadas = 0
        for via in vias:
            nome_via = via.get("nome_via")
            place_id = via.get("place_id")
            if not nome_via or not place_id:
                continue

            JurisdicaoService.adicionar_via(admin_id, nome_via, place_id, via.get("geometria"))
            adicionadas += 1

        return Response({"message": f"{adicionadas} via(s) adicionada(s) à jurisdição", "total": adicionadas})

    @swagger_auto_schema(
        operation_description="Remover uma via da jurisdição de um posto"
    )
    @action(detail=False, methods=["delete"], url_path="admin/(?P<admin_id>[^/.]+)/vias/(?P<via_id>[^/.]+)")
    def remover_via_jurisdicao(self, request, admin_id=None, via_id=None):
        JurisdicaoService.remover_via(admin_id, via_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

