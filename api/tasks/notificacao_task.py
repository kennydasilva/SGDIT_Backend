from celery import shared_task


@shared_task
def notificar_admin_acidente(denuncia_id):
    """
    Notifica por SMS (MozeSMS) o Admin do posto cuja jurisdição cobre o
    local do acidente - nunca todos os agentes/postos, só o responsável
    pela zona, que é quem decide qual agente enviar ao local.

    Se a denúncia não tiver `admin_responsavel` (localização fora de
    qualquer jurisdição registada) ou o admin não tiver telefone
    registado, não há para onde enviar - fica só visível nas listagens.

    Sem retry automático: um SMS já aceite pela MozeSMS e repetido por
    causa de uma falha posterior chegaria em duplicado (e é cobrado).
    """
    from api.model.denuncia import Denuncia
    from api.service.sms_service import SmsService

    denuncia = Denuncia.objects.select_related("admin_responsavel__utilizador").get(id=denuncia_id)

    admin = denuncia.admin_responsavel
    if not admin or not admin.utilizador.numero:
        return

    local = denuncia.localizacao or "local nao especificado"
    mensagem = f"SGDIT: Acidente de viacao reportado em {local}. Denuncia #{denuncia.id}. Designe um agente no painel."

    SmsService.enviar_sms(admin.utilizador.numero, mensagem)

