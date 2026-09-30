from celery import shared_task

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, max_retries=3)
def processar_analise_async(self, tipo, path, denuncia_id, sentido_direccao):

    from api.model.denuncia import Denuncia
    from api.Analise.Contramao import main_contramao
    from api.Analise.parado import main_parado
    from api.Analise.velocidade import main_velocidade

    from api.model.analise import ResultadoAnalise

    from api.service.assinatura_video_service import AssinaturaVideoService

    denuncia = Denuncia.objects.get(id=denuncia_id)

    # Antes da IA: liga a outra denúncia se o vídeo for visualmente igual
    # (cortado/recomprimido). Nunca impede a análise.
    AssinaturaVideoService.processar(denuncia)
    denuncia.refresh_from_db()

    try:
        if tipo == "CONTRAMAO":
            main_contramao(path, denuncia, sentido_direccao)

        elif tipo == "PARADO":
            main_parado(path, denuncia)

        elif tipo == "VELOCIDADE":
            main_velocidade(path, denuncia)

        # Os módulos de análise fazem só `return` quando não conseguem abrir
        # o vídeo (sem lançar erro) - sem esta verificação o Celery nunca
        # tentava de novo e a denúncia ficava pendente para sempre.
        if not ResultadoAnalise.objects.filter(denuncia_id=denuncia_id).exists():
            raise RuntimeError(f"Análise da denúncia {denuncia_id} terminou sem resultado")

    except Exception:
        # Esgotadas as tentativas: o sistema filtra denúncias - o que o
        # modelo não consegue analisar é rejeitado (decisão do
        # utilizador), e o cidadão é avisado do motivo.
        if self.request.retries >= self.max_retries:
            from api.service.notificacao_service import NotificacaoService

            denuncia.refresh_from_db()
            if denuncia.estado == Denuncia.Estado.PENDENTE:
                denuncia.estado = Denuncia.Estado.REJEITADA
                denuncia.save(update_fields=["estado", "atualizado_em"])
                NotificacaoService.analise_falhou(denuncia)
        raise


        