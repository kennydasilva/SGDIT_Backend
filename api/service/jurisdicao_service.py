from api.helper.geo import bounds_do_poligono, ponto_dentro_poligono, recortar_sobreposicao
from api.model.jurisdicao import ViaJurisdicao
from api.model.user import Admin


class ZonaSobrepostaError(Exception):
    """A área pedida para a zona já pertence inteiramente a zona(s) existentes."""


class JurisdicaoService:

    @staticmethod
    def listar_por_admin(admin_id):
        return ViaJurisdicao.objects.filter(admin_id=admin_id).order_by("nome_via")

    @staticmethod
    def adicionar_via(admin_id, nome_via, place_id, geometria=None):
        admin = Admin.objects.get(id=admin_id)

        via, _ = ViaJurisdicao.objects.update_or_create(
            admin=admin,
            place_id=place_id,
            defaults={"nome_via": nome_via, "geometria": geometria},
        )
        return via

    @staticmethod
    def adicionar_zona(admin_id, nome, place_id, poligono_geojson):
        """
        Atribui uma zona (contorno real de um bairro) a um posto - igual ao
        `adicionar_via`, mas para polígonos, com o mesmo comportamento do
        `resolveClippedMultiPolygon` do TruckFreightEasy: se a forma pedida
        cruza com zonas já existentes (de qualquer posto - uma zona só pode
        pertencer a um posto de cada vez), a parte já coberta é recortada
        automaticamente antes de guardar. As zonas nunca ficam sobrepostas.

        Levanta `ZonaSobrepostaError` se, depois de recortar contra tudo o
        que já existe, não sobrar nenhuma área (a forma pedida já pertencia
        inteiramente a outra(s) zona(s)).
        """
        poligonos_existentes = [
            geometria["polygon"]
            for geometria in ViaJurisdicao.objects.exclude(geometria__isnull=True).values_list("geometria", flat=True)
            if geometria and geometria.get("polygon")
        ]

        poligono_recortado = recortar_sobreposicao(poligono_geojson, poligonos_existentes)
        if poligono_recortado is None:
            raise ZonaSobrepostaError(
                "Esta área já pertence inteiramente a uma zona existente (de qualquer posto)."
            )

        bounds = bounds_do_poligono(poligono_recortado)
        centro = {
            "lat": (bounds["north"] + bounds["south"]) / 2,
            "lng": (bounds["east"] + bounds["west"]) / 2,
        }

        return JurisdicaoService.adicionar_via(
            admin_id,
            nome,
            place_id,
            {**centro, "bounds": bounds, "polygon": poligono_recortado},
        )

    @staticmethod
    def reencaminhar_sem_posto():
        """
        Denúncias abertas que caíram fora de qualquer jurisdição e que,
        com as zonas/vias actuais, já têm posto: passam para esse posto.
        Chamado ao criar uma zona ou vias (e pelo botão no mapa de
        cobertura). Só PENDENTE/VALIDADA - as já decididas ficam como estão.

        Acidente PENDENTE sem posto -> ENCAMINHADA, com notificação ao Admin
        e ao cidadão; SMS só se o acidente tiver menos de 2 h (um SMS de um
        acidente de há dias já não serve e é pago).

        Devolve {"total", "acidentes", "sms", "por_posto": {posto: n}}.
        """
        from datetime import timedelta

        from django.utils import timezone

        from api.model.denuncia import Denuncia
        from api.service.notificacao_service import NotificacaoService
        from api.tasks.notificacao_task import notificar_admin_acidente

        candidatas = Denuncia.objects.filter(
            admin_responsavel__isnull=True,
            estado__in=[Denuncia.Estado.PENDENTE, Denuncia.Estado.VALIDADA],
        ).exclude(latitude__isnull=True).exclude(longitude__isnull=True).select_related("cidadao__utilizador")

        resultado = {"total": 0, "acidentes": 0, "sms": 0, "por_posto": {}}
        limite_sms = timezone.now() - timedelta(hours=2)

        for d in candidatas:
            admin = JurisdicaoService.encontrar_admin_por_localizacao(d.latitude, d.longitude)
            if not admin:
                continue

            d.admin_responsavel = admin
            campos = ["admin_responsavel", "atualizado_em"]
            eh_acidente = d.tipo_infracao == Denuncia.tipoInfracao.ACIDENTE

            if eh_acidente and d.estado == Denuncia.Estado.PENDENTE:
                d.estado = Denuncia.Estado.ENCAMINHADA
                campos.append("estado")
            d.save(update_fields=campos)

            if eh_acidente:
                resultado["acidentes"] += 1
                NotificacaoService.estado_alterado(d)
                NotificacaoService.notificar(
                    [admin.utilizador],
                    "ACIDENTE_REPORTADO",
                    f"Acidente de viação #{d.id} (reencaminhado)",
                    f"Acidente em {d.localizacao or 'local não especificado'}, reportado a "
                    f"{timezone.localtime(d.data_registo).strftime('%d/%m %H:%M')}, passou para a jurisdição "
                    f"do seu posto (nova zona). Designe um agente, se ainda for necessário.",
                    d,
                )
                if d.data_registo >= limite_sms and not d.denuncia_principal_id:
                    notificar_admin_acidente.apply_async(args=[d.id], countdown=2)
                    resultado["sms"] += 1

            resultado["total"] += 1
            resultado["por_posto"][admin.posto] = resultado["por_posto"].get(admin.posto, 0) + 1

        return resultado

    @staticmethod
    def remover_via(admin_id, via_id):
        ViaJurisdicao.objects.filter(admin_id=admin_id, id=via_id).delete()

    @staticmethod
    def encontrar_admin_por_place_id(place_id):
        via = ViaJurisdicao.objects.filter(place_id=place_id).select_related("admin").first()
        return via.admin if via else None

    @staticmethod
    def encontrar_admin_por_localizacao(latitude, longitude):
        """
        Determina o posto (Admin) responsável por uma coordenada.

        Duas fontes de geometria em `ViaJurisdicao.geometria`, por ordem de
        confiança:
        1. `polygon` (GeoJSON Polygon/MultiPolygon) - o contorno real de uma
           "zona" (bairro inteiro), obtido do Nominatim. Testado por
           ponto-dentro-do-polígono (preciso, segue a fronteira real).
        2. `bounds` (rectângulo aproximado) - vias individuais ou zonas
           antigas só com viewport. Testado por ponto dentro do rectângulo.

        Um polígono que bate sempre ganha a um rectângulo (é sempre mais
        preciso). Dentro do mesmo tipo, ganha a menor área (match mais
        específico) - reduz o risco de sobreposição entre bounds/polígonos
        aproximados de zonas vizinhas escolher o posto errado.
        """
        if latitude is None or longitude is None:
            return None

        melhor_admin_poligono, menor_area_poligono = None, None
        melhor_admin_bounds, menor_area_bounds = None, None

        for via in ViaJurisdicao.objects.select_related("admin").exclude(geometria__isnull=True):
            geometria = via.geometria or {}

            poligono = geometria.get("polygon")
            if poligono and ponto_dentro_poligono(latitude, longitude, poligono):
                bounds = bounds_do_poligono(poligono)
                area = (bounds["north"] - bounds["south"]) * (bounds["east"] - bounds["west"])
                if menor_area_poligono is None or area < menor_area_poligono:
                    menor_area_poligono = area
                    melhor_admin_poligono = via.admin
                continue

            bounds = geometria.get("bounds")
            if not bounds:
                continue

            norte, sul = bounds.get("north"), bounds.get("south")
            este, oeste = bounds.get("east"), bounds.get("west")
            if None in (norte, sul, este, oeste):
                continue

            if not (sul <= latitude <= norte and oeste <= longitude <= este):
                continue

            area = (norte - sul) * (este - oeste)
            if menor_area_bounds is None or area < menor_area_bounds:
                menor_area_bounds = area
                melhor_admin_bounds = via.admin

        return melhor_admin_poligono or melhor_admin_bounds
