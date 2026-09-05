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
