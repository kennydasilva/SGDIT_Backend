from celery import shared_task
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import action

from api.model.denuncia import Denuncia
from api.service.denucia_service import DenunciaService
from api.serializers.denuncia_serializer import (
    DenunciaCreateSerializer,
    DenunciaResponseSerializer,
    DenunciaUpdateSerializer,
)

from api.Analise.Contramao import main_contramao
from api.Analise.parado import main_parado
from api.Analise.velocidade import main_velocidade
from api.service.evidencia_service import EvidenciaService
import re
import threading
from django.core.cache import cache
import traceback
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from api.service.resultado_analise_service import ResultadoAnaliseService
from api.tasks.analise_task import processar_analise_async
from api.tasks.notificacao_task import notificar_admin_acidente
from api.service.duplicados_service import DuplicadosService
from api.helper.dataConvertion import formatar_data
from api.pagination import PaginacaoPadrao
from api.permissions.role_permissions import IsAdmin, IsAdminOrSuperAdmin

class DenunciaViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = PaginacaoPadrao

    CAMPOS_ORDENACAO_VALIDOS = {"id", "data_registo", "estado", "matricula", "tipo_infracao"}

    def _ordenar(self, queryset, request):
        ordering = request.query_params.get("ordering", "-data_registo")
        campo = ordering.lstrip("-")

        if campo not in self.CAMPOS_ORDENACAO_VALIDOS:
            ordering = "-data_registo"

        return queryset.order_by(ordering)

    def _listar_paginado(self, request, denuncias):

        denuncias = self._ordenar(denuncias, request)

        paginator = self.pagination_class()
        pagina = paginator.paginate_queryset(denuncias, request, view=self)

        data = []

        for d in pagina:

            resultadoAnalise = ResultadoAnaliseService.obter_por_denuncia(d.id)
            evidencia = EvidenciaService.obter_evidencia(d.id)

            ficheiro_processado = (
                resultadoAnalise.caminho_ficheiro_processado.url
                if resultadoAnalise and resultadoAnalise.caminho_ficheiro_processado
                else None
            )

            ficheiro_original = (
                evidencia.caminho_ficheiro.url
                if evidencia and evidencia.caminho_ficheiro
                else None
            )

            data_captura_formatada = formatar_data(evidencia.data_captura) if evidencia else None
            data_analise_formatada = formatar_data(resultadoAnalise.data_analise) if resultadoAnalise else None

            data.append(DenunciaViewSet.preparar_denuncia(d, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada))

        return paginator.get_paginated_response(data)

    @swagger_auto_schema(
        operation_description="Listar todas denuncias (paginado; ?page=&page_size=&ordering=)",
        responses={200: "sucesso na requisicao"}
    )
    def list(self, request):
        return self._listar_paginado(request, DenunciaService.listar_denuncias())


        
        




    @swagger_auto_schema(
        operation_description="Obter denuncia por ID",
        responses={200: DenunciaResponseSerializer}
    )
    def retrieve(self, request, pk=None):

        denuncia = DenunciaService.obter_denuncia_por_id(pk)

        if not denuncia:
            return Response(
                {"error": "Denuncia nao encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )       

        resultadoAnalise = ResultadoAnaliseService.obter_por_denuncia(denuncia.id)
        evidencia = EvidenciaService.obter_evidencia(denuncia.id)

        ficheiro_processado = (
                resultadoAnalise.caminho_ficheiro_processado.url
                if resultadoAnalise and resultadoAnalise.caminho_ficheiro_processado
                else None
        )

        ficheiro_original = (
                evidencia.caminho_ficheiro.url
                if evidencia and evidencia.caminho_ficheiro
                else None
        )


        data_captura_formatada = formatar_data(evidencia.data_captura) if evidencia else None
        data_analise_formatada = formatar_data(resultadoAnalise.data_analise) if resultadoAnalise else None

        data= DenunciaViewSet.preparar_denuncia(denuncia, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada)

        return Response(data)



    

  



    @swagger_auto_schema(
        operation_description="Criar denuncia",
        request_body=DenunciaCreateSerializer,
        consumes=['multipart/form-data'] 
    )
    def create(self, request):
        from rest_framework.parsers import MultiPartParser, FormParser
        from django.conf import settings

        chave_pedido = None
        chaves_bloqueio = []

        def _recusar_duplicada(mensagem, **extra):
            # Liberta o pedido (o cidadão pode corrigir e reenviar o mesmo
            # formulário) e os bloqueios tomados por este pedido.
            if chave_pedido:
                cache.delete(chave_pedido)
            for chave in chaves_bloqueio:
                cache.delete(chave)
            return Response(
                {"error": mensagem, "codigo": "DUPLICADA", **extra},
                status=status.HTTP_409_CONFLICT
            )

        try:

            sentido_direccao = request.data.get("sentido_direccao")
            tipo_infracao = request.data.get("tipo_infracao")
            eh_acidente = tipo_infracao == Denuncia.tipoInfracao.ACIDENTE

            ficheiro = request.FILES.get("caminho_ficheiro")

            # Obrigatória em todos os tipos excepto acidente (quem reporta
            # pode não ver/saber a matrícula); quando enviada, tem sempre de
            # ser válida.
            matricula = (request.data.get("matricula") or "").strip()
            if (matricula or not eh_acidente) and not re.fullmatch(r"[A-Za-z]{2}-\d{2}-[A-Za-z]{2}", matricula):
                return Response({"error": "Matrícula inválida (formato AB-12-CD)"}, status=400)

            # Acidente de viação é reporte direto ao posto responsável, sem
            # análise de vídeo por IA (não há tempo para isso) - por isso
            # não exige ficheiro, ao contrário dos outros tipos de denúncia.
            if not ficheiro and not eh_acidente:
                return Response({"error": "Ficheiro não enviado"}, status=400)

            if ficheiro:
                formatos_validos = ('.mp4', '.avi', '.mov', '.jpg', '.jpeg', '.png') if eh_acidente else ('.mp4', '.avi', '.mov')
                if not ficheiro.name.lower().endswith(formatos_validos):
                    return Response({"error": "Formato inválido"}, status=400)

                max_size_mb = getattr(settings, "DENUNCIA_VIDEO_MAX_SIZE_MB", 100)
                if ficheiro.size > max_size_mb * 1024 * 1024:
                    return Response(
                        {"error": f"Ficheiro demasiado grande (máximo {max_size_mb}MB). Reduza a duração/qualidade."},
                        status=400
                    )

            def _para_float(valor):
                try:
                    return float(valor) if valor not in (None, "") else None
                except (TypeError, ValueError):
                    return None

            # Protecção contra duplo clique/reenvio: o frontend gera um
            # `pedido_id` único por formulário. `cache.add` é atómico no
            # Redis - só o primeiro pedido com esse id passa; os repetidos
            # recebem 409 (com o id da denúncia, se já foi criada).
            pedido_id = request.data.get("pedido_id")
            if pedido_id:
                chave_pedido = f"denuncia_pedido:{request.user.id}:{pedido_id}"
                if not cache.add(chave_pedido, "a_processar", timeout=600):
                    existente = cache.get(chave_pedido)
                    chave_pedido = None  # não apagar a chave do pedido original
                    return Response(
                        {
                            "error": "Esta denúncia já foi enviada",
                            "codigo": "PEDIDO_REPETIDO",
                            "id": existente if isinstance(existente, int) else None,
                        },
                        status=status.HTTP_409_CONFLICT
                    )

            latitude = _para_float(request.data.get("latitude"))
            longitude = _para_float(request.data.get("longitude"))
            cidadao = DenunciaService.encontrar_utilizador_cidadao(request.data.get("cidadao_id"))

            # Regra 1: o mesmo ficheiro nunca entra em duas denúncias. O
            # bloqueio no Redis cobre dois envios simultâneos do mesmo
            # ficheiro (ainda nenhum gravado na BD quando ambos verificam).
            hash_ficheiro = None
            if ficheiro:
                hash_ficheiro = DuplicadosService.calcular_hash(ficheiro)
                usada = DuplicadosService.ficheiro_ja_usado(hash_ficheiro)
                chave_hash = f"evidencia_hash:{hash_ficheiro}"
                if usada or not cache.add(chave_hash, 1, timeout=600):
                    # Só mostra o número se a denúncia for do próprio
                    # cidadão - nunca revelar denúncias de outros.
                    propria = usada and usada.denuncia.cidadao_id == cidadao.id
                    return _recusar_duplicada(
                        f"Este ficheiro já foi enviado na denúncia #{usada.denuncia_id}." if propria
                        else "Este ficheiro já foi enviado numa denúncia anterior.",
                        id=usada.denuncia_id if propria else None,
                    )
                chaves_bloqueio.append(chave_hash)

            # Regra 2: o mesmo cidadão não abre duas denúncias para a
            # mesma coisa enquanto a anterior não estiver fechada.
            aberta = DuplicadosService.denuncia_aberta_do_cidadao(
                cidadao.id, tipo_infracao, matricula, latitude, longitude
            )
            if aberta:
                return _recusar_duplicada(
                    f"Já tem uma denúncia aberta para esta ocorrência (#{aberta.id}). "
                    "Aguarde a decisão antes de denunciar de novo.",
                    id=aberta.id,
                )

            denuncia = DenunciaService.criar_denuncia(
                request.data.get("cidadao_id"),
                matricula.upper(),
                request.data.get("descricao"),
                tipo_infracao,
                request.data.get("localizacao"),
                request.data.get("sentido_direccao"),
                latitude,
                longitude
            )

            if ficheiro:
                EvidenciaService.criar_evidencia(denuncia, ficheiro, hash_ficheiro)

            if eh_acidente and denuncia.denuncia_principal_id:
                # Reporte de um acidente já reportado: o Admin já recebeu o
                # SMS do primeiro; recebe só a notificação na aplicação.
                pass
            elif eh_acidente:
                # Notifica só o Admin do posto cuja jurisdição cobre o local
                # (já determinado em criar_denuncia) - nunca todos os
                # agentes; é o Admin que decide quem vai ao local.
                notificar_admin_acidente.apply_async(args=[denuncia.id], countdown=2)
            else:
                evidencia = EvidenciaService.obter_evidencia(denuncia.id)
                processar_analise_async.apply_async(
                    args=[
                        denuncia.tipo_infracao,
                        evidencia.caminho_ficheiro.path,
                        denuncia.id,
                        sentido_direccao
                    ],
                    countdown=5
                )

            if chave_pedido:
                cache.set(chave_pedido, denuncia.id, timeout=600)

            return Response(
                {"message": "Denuncia criada com sucesso", "id": denuncia.id},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:

            # Falhou a criar: liberta o pedido para o cidadão poder tentar
            # outra vez com o mesmo formulário.
            if chave_pedido:
                cache.delete(chave_pedido)
            for chave in chaves_bloqueio:
                cache.delete(chave)
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


        

    @swagger_auto_schema(
        operation_description="Actualizar estado da denuncia user PT",
        request_body=DenunciaUpdateSerializer
    )
    @action(detail=False, methods=["patch"], url_path="pt/actualizar", 
     parser_classes=[JSONParser, MultiPartParser])
    def actualizar_estado(self, request, data=None):

        denuncia_id = int(request.data.get("denuncia_id"))
        estado = request.data.get("estado")
        codigo_legal = request.data.get("codigo_legal")
        descricao_pt = request.data.get("descricao_pt")
        pt_id = int(request.data.get("pt_id"))

       

        denuncia = DenunciaService.actualizar_estado_PT(denuncia_id, estado, codigo_legal, descricao_pt, pt_id)

        return Response(denuncia.id, status=status.HTTP_200_OK)





    @swagger_auto_schema(
        operation_description="Apagar denuncia"
    )
    def destroy(self, request, pk=None):

        denuncia=DenunciaService.obter_denuncia_por_id(pk)
        evidencia=EvidenciaService.obter_evidencia(denuncia.id)
        
        resultadoAnalise=ResultadoAnaliseService.obter_por_denuncia(denuncia.id)

        if evidencia is not None:
            evidencia.delete()

        if resultadoAnalise is not None:
            resultadoAnalise.delete()

        DenunciaService.apagar_denuncia(pk)

        return Response(status=status.HTTP_204_NO_CONTENT)

        

    @swagger_auto_schema(
        operation_description="Listar denuncias por cidadao (paginado; ?page=&page_size=&ordering=)"
    )
    @action(detail=False, methods=["get"], url_path="cidadao/(?P<cidadao_id>[^/.]+)")
    def por_cidadao(self, request, cidadao_id=None):
        return self._listar_paginado(request, DenunciaService.listar_por_cidadao(cidadao_id))

    @swagger_auto_schema(
        operation_description="Listar denuncias validadas, restrito ao posto do PT autenticado "
                               "(+ denuncias sem posto determinado) (paginado; ?page=&page_size=&ordering=)"
    )
    @action(detail=False, methods=["get"], url_path="pt/validadas")
    def por_validadas(self, request):
        pt = getattr(request.user, "pt", None)
        admin_id = pt.admin_id if pt else None
        return self._listar_paginado(request, DenunciaService.listar_denuncias_validadas(admin_id))

    @swagger_auto_schema(
        operation_description="Listar denuncias por PT (paginado; ?page=&page_size=&ordering=)"
    )
    @action(detail=False, methods=["get"], url_path="pt/denuncias/(?P<pt_id>[^/.]+)")
    def por_pt(self, request, pt_id=None):
        return self._listar_paginado(request, DenunciaService.listar_por_pt(pt_id))

    @swagger_auto_schema(
        operation_description="Listar acidentes de viação na jurisdição do posto do Admin autenticado "
                               "(paginado; ?page=&page_size=&ordering=)"
    )
    @action(
        detail=False, methods=["get"],
        url_path="admin/acidentes",
        permission_classes=[IsAdmin]
    )
    def acidentes_por_admin(self, request):
        # Posto lido do utilizador autenticado, nunca de um parâmetro do
        # pedido - um Admin não pode ver os acidentes de outro posto.
        admin = getattr(request.user, "admin", None)
        if not admin:
            return Response({"error": "Utilizador sem posto associado"}, status=403)

        return self._listar_paginado(request, DenunciaService.listar_acidentes_por_admin(admin.id))

    @swagger_auto_schema(
        operation_description="Admin designa o agente (PT) que vai atender um acidente na sua jurisdição",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "denuncia_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "pt_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        )
    )
    @action(
        detail=False, methods=["patch"],
        url_path="admin/designar-pt",
        permission_classes=[IsAdmin]
    )
    def designar_pt_acidente(self, request):
        denuncia_id = request.data.get("denuncia_id")
        pt_id = request.data.get("pt_id")

        if not denuncia_id or not pt_id:
            return Response({"error": "denuncia_id e pt_id são obrigatórios"}, status=400)

        admin = getattr(request.user, "admin", None)
        if not admin:
            return Response({"error": "Utilizador sem posto associado"}, status=403)

        try:
            denuncia = DenunciaService.designar_pt_acidente(denuncia_id, pt_id, admin.id)
        except Denuncia.DoesNotExist:
            return Response({"error": "Acidente não encontrado nesta jurisdição"}, status=404)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        return Response({"message": "Agente designado", "id": denuncia.id})

    def preparar_denuncia(denuncia, resultadoAnalise, ficheiro_processado, ficheiro_original, data_captura_formatada, data_analise_formatada):
        data={
                "id": denuncia.id,
                "matricula": denuncia.matricula,
                "estado": denuncia.estado,
                "descricao": denuncia.descricao,
                "tipo_infracao": denuncia.tipo_infracao,
                "localizacao": denuncia.localizacao,
                "latitude": denuncia.latitude,
                "longitude": denuncia.longitude,
                "sentido_direccao": denuncia.sentido_direccao,
                "pt_id": denuncia.pt_id,
                "admin_responsavel_id": denuncia.admin_responsavel_id,
                "data_registo": formatar_data(denuncia.data_registo),
                "denuncia_principal_id": denuncia.denuncia_principal_id,
                "total_relacionadas": denuncia.relacionadas.count(),
                "ficheiro_processado": ficheiro_processado,
                "ficheiro_original": ficheiro_original,
                "data_captura": data_captura_formatada,
                "codigo_legal": resultadoAnalise.codigo_legal if resultadoAnalise else None,
                "confianca": resultadoAnalise.confianca if resultadoAnalise else None,
                "data_analise": data_analise_formatada,
                "infracao_detectada": resultadoAnalise.infracao_detectada if resultadoAnalise else None,
        }

        return data