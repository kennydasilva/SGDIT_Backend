from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, max_retries=3)
def notificar_admin_acidente(self, denuncia_id):
    """
    Notifica (push, via Firebase) o Admin do posto cuja jurisdição cobre o
    local do acidente - nunca todos os agentes/postos, só o responsável
    pela zona, que é quem decide qual(is) agente(s) enviar ao local.

    Se a denúncia ainda não tiver `admin_responsavel` (localização fora de
    qualquer jurisdição registada) ou o admin não tiver `fcm_token`
    registado (nunca abriu a app/dashboard para autorizar notificações),
    não há para onde enviar - fica só visível nas listagens normais.
    """
    from api.model.denuncia import Denuncia
    from api.service.firebase_service import FirebaseService

    denuncia = Denuncia.objects.select_related("admin_responsavel__utilizador").get(id=denuncia_id)

    admin = denuncia.admin_responsavel
    if not admin or not admin.utilizador.fcm_token:
        return

    FirebaseService.enviar_notificacao(
        token=admin.utilizador.fcm_token,
        titulo="Acidente de viação reportado",
        corpo=denuncia.localizacao or "Localização não especificada",
        dados={"tipo": "ACIDENTE", "denuncia_id": denuncia.id},
    )
