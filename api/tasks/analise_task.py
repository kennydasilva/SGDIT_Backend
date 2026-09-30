from celery import shared_task

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, max_retries=3)
def processar_analise_async(self, tipo, path, denuncia_id, sentido_direccao):

    from api.model.denuncia import Denuncia
    from api.Analise.Contramao import main_contramao
    from api.Analise.parado import main_parado
    from api.Analise.velocidade import main_velocidade

    denuncia = Denuncia.objects.get(id=denuncia_id)

    try:
        if tipo == "CONTRAMAO":
            main_contramao(path, denuncia, sentido_direccao)

        elif tipo == "PARADO":
            main_parado(path, denuncia)

        elif tipo == "VELOCIDADE":
            main_velocidade(path, denuncia)

    except Exception:
        # Última tentativa falhou: avisa o cidadão, senão a denúncia fica
        # pendente para sempre sem ele saber porquê.
        if self.request.retries >= self.max_retries:
            from api.service.notificacao_service import NotificacaoService
            NotificacaoService.analise_falhou(denuncia)
        raise


        