import logging

import requests
from django.core.cache import cache

from api.helper.http_retry import com_retry

logger = logging.getLogger(__name__)

_URL_OVERPASS = "https://overpass-api.de/api/interpreter"
_USER_AGENT = "SGDIT-Backend/1.0 (jurisdicao-service)"
_CACHE_TTL_SEGUNDOS = 60 * 60 * 24  # 1 dia - a rede de vias de um bairro não muda de um dia para o outro


class OverpassService:
    """
    Lista, de uma vez, todas as vias nomeadas dentro de um bairro (via
    OpenStreetMap Overpass API), a partir do bairro encontrado com
    NominatimService.pesquisar_bairros. Poupa o Super Admin de ter de
    pesquisar e adicionar via a via manualmente quando quer cobrir um
    bairro inteiro.

    Cacheado (Redis, 1 dia) - o Overpass público é instável sob uso
    repetido, e a rede de vias de um bairro não muda de um dia para o
    outro.
    """

    @staticmethod
    def listar_vias_do_bairro(osm_type, osm_id):
        chave_cache = f"overpass_vias_bairro:{osm_type}:{osm_id}"
        em_cache = cache.get(chave_cache)
        if em_cache is not None:
            return em_cache

        query = (
            f"[out:json][timeout:25];{osm_type}({osm_id});"
            "map_to_area->.a;way(area.a)[highway][name];out tags geom;"
        )

        def _pedir():
            resposta = requests.get(
                _URL_OVERPASS,
                params={"data": query},
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            resposta.raise_for_status()
            return resposta.json().get("elements", [])

        try:
            elementos = com_retry(_pedir, tentativas=3, espera_segundos=2, nome="Overpass (vias do bairro)")
        except Exception:
            logger.exception("Falha ao pesquisar vias do bairro no Overpass, mesmo depois de repetir")
            return None

        vias = OverpassService._agrupar_por_nome(elementos, osm_type, osm_id)
        cache.set(chave_cache, vias, _CACHE_TTL_SEGUNDOS)
        return vias

    @staticmethod
    def _agrupar_por_nome(elementos, osm_type, osm_id):
        """
        Uma via costuma vir partida em vários troços (`way`) no OSM, um por
        cada interseção - agrupamos por nome para dar UMA entrada por via,
        com os limites (bounds) a cobrirem todos os troços.
        """
        grupos = {}

        for elemento in elementos:
            nome = elemento.get("tags", {}).get("name")
            geometria = elemento.get("geometry") or []
            if not nome or not geometria:
                continue

            grupo = grupos.setdefault(nome, {"lats": [], "lngs": []})
            for ponto in geometria:
                if "lat" in ponto and "lon" in ponto:
                    grupo["lats"].append(ponto["lat"])
                    grupo["lngs"].append(ponto["lon"])

        vias = []
        for nome, grupo in sorted(grupos.items()):
            if not grupo["lats"]:
                continue

            norte, sul = max(grupo["lats"]), min(grupo["lats"])
            este, oeste = max(grupo["lngs"]), min(grupo["lngs"])

            vias.append({
                "nome_via": nome,
                "place_id": f"osm:bairro:{osm_type}:{osm_id}:{nome}",
                "geometria": {
                    "lat": (norte + sul) / 2,
                    "lng": (este + oeste) / 2,
                    "bounds": {"north": norte, "south": sul, "east": este, "west": oeste},
                },
            })

        return vias
