from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from api.service.configuracao_service import ConfiguracaoService


class ConfiguracaoPublicaController(APIView):
    """
    Devolve só as credenciais marcadas como 'publica' (ex: chave JS do
    Google Maps, protegida por restrição de domínio na Google Cloud
    Console) - acessível a qualquer utilizador autenticado, nunca a
    segredos de servidor (ex: Firebase Admin SDK).
    """

    @swagger_auto_schema(
        operation_description="Obter configurações públicas (ex: chave do Google Maps)"
    )
    def get(self, request):
        return Response(ConfiguracaoService.listar_publicas())
