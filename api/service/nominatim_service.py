import logging

import requests

from api.helper.http_retry import com_retry

logger = logging.getLogger(__name__)

_URL_PESQUISA = "https://nominatim.openstreetmap.org/search"
_URL_LOOKUP = "https://nominatim.openstreetmap.org/lookup"
_USER_AGENT = "SGDIT-Backend/1.0 (jurisdicao-service)"

# Nominatim identifica elementos OSM com um prefixo de 1 letra por tipo
_PREFIXO_OSM_TYPE = {"node": "N", "way": "W", "relation": "R"}


class NominatimService:
    """
    Pesquisa de vias/estradas via OpenStreetMap Nominatim, usada para
    atribuir vias à jurisdição de um posto (Super Admin).

    Trocado a partir do Google Places Autocomplete: o Google não distingue
    uma via de um estabelecimento (POI) qualquer no meio dela - pesquisar o
    nome de um bairro (ex: "Albazine") podia devolver como primeiro
    resultado um POI lá dentro (ex: "Terminal de Albazine"), cujo viewport é
    só o desse ponto, não cobre as vias do bairro. O Nominatim classifica
    resultados por `class`/`type` (`class=highway` = via/estrada), o que
    permite filtrar por vias a sério.

    Sem chave de API (serviço público), mas com limite de uso do provedor
    (~1 pedido/seg) - suficiente para uma ferramenta interna de baixo
    tráfego (Super Admin a configurar jurisdições), não para pesquisa em
    massa. Requer um User-Agent identificável, exigido pela política de uso
    do Nominatim.
    """

    @staticmethod
    def pesquisar_vias(query, limite=8):
        if not query or len(query.strip()) < 3:
            return []

        def _pedir():
            resposta = requests.get(
                _URL_PESQUISA,
                params={
                    "q": query,
                    "format": "jsonv2",
                    "countrycodes": "mz",
                    "limit": limite * 3,  # pede a mais, filtra a seguir a só vias
                    "addressdetails": 1,
                },
                headers={"User-Agent": _USER_AGENT},
                timeout=8,
            )
            resposta.raise_for_status()
            return resposta.json()

        try:
            resultados = com_retry(_pedir, nome="Nominatim (pesquisar vias)")
        except Exception:
            logger.exception("Falha ao pesquisar vias no Nominatim, mesmo depois de repetir")
            return []

        vias = [r for r in resultados if r.get("category") == "highway"]

        return [
            {
                "nome_via": r.get("display_name"),
                "place_id": f"osm:{r.get('osm_type')}:{r.get('osm_id')}",
                "tipo_via": r.get("type"),
                "geometria": NominatimService._extrair_geometria(r),
            }
            for r in vias[:limite]
        ]

    # Bairros/localidades (addresstype neighbourhood/suburb/quarter/city_district)
    # - usado para encontrar a área a passar ao Overpass (listar_vias_do_bairro),
    # não para atribuir jurisdição directamente (essa continua a ser por via).
    _TIPOS_BAIRRO = {"neighbourhood", "suburb", "quarter", "city_district", "borough"}

    @staticmethod
    def pesquisar_bairros(query, limite=6):
        if not query or len(query.strip()) < 3:
            return []

        def _pedir():
            resposta = requests.get(
                _URL_PESQUISA,
                params={
                    "q": query,
                    "format": "jsonv2",
                    "countrycodes": "mz",
                    "limit": limite * 3,
                },
                headers={"User-Agent": _USER_AGENT},
                timeout=8,
            )
            resposta.raise_for_status()
            return resposta.json()

        try:
            resultados = com_retry(_pedir, nome="Nominatim (pesquisar bairros)")
        except Exception:
            logger.exception("Falha ao pesquisar bairros no Nominatim, mesmo depois de repetir")
            return []

        bairros = [r for r in resultados if r.get("addresstype") in NominatimService._TIPOS_BAIRRO]

        resultado = []
        for r in bairros[:limite]:
            try:
                lat, lng = float(r["lat"]), float(r["lon"])
            except (KeyError, TypeError, ValueError):
                lat = lng = None

            resultado.append({
                "nome": r.get("name") or r.get("display_name"),
                "display_name": r.get("display_name"),
                "osm_type": r.get("osm_type"),
                "osm_id": r.get("osm_id"),
                "lat": lat,
                "lng": lng,
            })

        return resultado

    @staticmethod
    def obter_poligono_bairro(osm_type, osm_id):
        """
        Contorno real (polígono, não um rectângulo aproximado) de um
        bairro/localidade - usado para atribuir uma "zona" inteira à
        jurisdição de um posto, em vez de vias avulsas. Pode ser um
        Polygon (uma área) ou MultiPolygon (várias áreas separadas) - o
        formato GeoJSON é devolvido tal e qual para o frontend desenhar, e
        `JurisdicaoService` usa `_pontos_dos_aneis()` para o teste
        ponto-dentro-do-polígono.
        """
        prefixo = _PREFIXO_OSM_TYPE.get(osm_type)
        if not prefixo:
            return None

        def _pedir():
            resposta = requests.get(
                _URL_LOOKUP,
                params={
                    "osm_ids": f"{prefixo}{osm_id}",
                    "format": "jsonv2",
                    "polygon_geojson": 1,
                },
                headers={"User-Agent": _USER_AGENT},
                timeout=10,
            )
            resposta.raise_for_status()
            return resposta.json()

        try:
            resultados = com_retry(_pedir, nome="Nominatim (polígono do bairro)")
        except Exception:
            logger.exception("Falha ao obter o polígono do bairro no Nominatim, mesmo depois de repetir")
            return None

        if not resultados:
            return None

        geojson = resultados[0].get("geojson")
        if not geojson or geojson.get("type") not in ("Polygon", "MultiPolygon"):
            return None

        return geojson

    @staticmethod
    def _extrair_geometria(resultado):
        try:
            lat = float(resultado["lat"])
            lng = float(resultado["lon"])
            sul, norte, oeste, este = (float(v) for v in resultado["boundingbox"])
        except (KeyError, TypeError, ValueError):
            return None

        return {
            "lat": lat,
            "lng": lng,
            "bounds": {"north": norte, "south": sul, "east": este, "west": oeste},
        }
