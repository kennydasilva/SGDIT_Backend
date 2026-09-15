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
        ViaJurisdicao.geometria para cada via/bairro da jurisdição.

        Não é o traçado exato da via nem o polígono real do bairro (o Google
        Places Autocomplete não devolve isso), mas é a mesma aproximação já
        usada para desenhar as vias no mapa de Jurisdições - suficiente para
        decidir qual posto notificar, sem depender de nenhuma API/geometria
        nova.

        Como agora é possível atribuir tanto uma via específica (retângulo
        pequeno) como um bairro inteiro (retângulo grande, ex: "Albazine"),
        os dois podem cobrir o mesmo ponto ao mesmo tempo - por exemplo, uma
        via só de um posto vizinho pode ter o retângulo a invadir ligeiramente
        o bairro de outro posto. Nesses casos escolhe-se sempre o retângulo
        de MENOR área (o match mais específico), em vez do primeiro
        encontrado - reduz o risco de notificar o posto errado por causa de
        sobreposição entre bounds aproximados.
        """
        if latitude is None or longitude is None:
            return None

        melhor_admin = None
        menor_area = None

        for via in ViaJurisdicao.objects.select_related("admin").exclude(geometria__isnull=True):
            bounds = (via.geometria or {}).get("bounds")
            if not bounds:
                continue

            norte, sul = bounds.get("north"), bounds.get("south")
            este, oeste = bounds.get("east"), bounds.get("west")
            if None in (norte, sul, este, oeste):
                continue

            if not (sul <= latitude <= norte and oeste <= longitude <= este):
                continue

            area = (norte - sul) * (este - oeste)
            if menor_area is None or area < menor_area:
                menor_area = area
                melhor_admin = via.admin

        return melhor_admin
