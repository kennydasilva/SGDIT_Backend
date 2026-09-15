from api.model.jurisdicao import ViaJurisdicao
from api.model.user import Admin


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
    def remover_via(admin_id, via_id):
        ViaJurisdicao.objects.filter(admin_id=admin_id, id=via_id).delete()

    @staticmethod
    def encontrar_admin_por_place_id(place_id):
        via = ViaJurisdicao.objects.filter(place_id=place_id).select_related("admin").first()
        return via.admin if via else None

    @staticmethod
    def encontrar_admin_por_localizacao(latitude, longitude):
        """
        Determina o posto (Admin) responsável por uma coordenada, a partir
        da área aproximada (bounds do viewport do Google) guardada em
        ViaJurisdicao.geometria para cada via da jurisdição.

        Não é o traçado exato da via (o Google Places Autocomplete não
        devolve isso), mas é a mesma aproximação já usada para desenhar as
        vias no mapa de Jurisdições - suficiente para decidir qual posto
        notificar, sem depender de nenhuma API/geometria nova.
        """
        if latitude is None or longitude is None:
            return None

        for via in ViaJurisdicao.objects.select_related("admin").exclude(geometria__isnull=True):
            bounds = (via.geometria or {}).get("bounds")
            if not bounds:
                continue

            if (
                bounds.get("south") <= latitude <= bounds.get("north")
                and bounds.get("west") <= longitude <= bounds.get("east")
            ):
                return via.admin

        return None
