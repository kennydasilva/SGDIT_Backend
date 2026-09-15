"""
Operações de geometria (zonas de jurisdição) usando shapely - o mesmo motor
(GEOS) que o PostGIS usa por trás, só que a correr dentro da própria
aplicação em vez de precisar de uma extensão na base de dados (este
Postgres não tem PostGIS disponível). Replica o que já era feito com
`fleetbase/laravel-mysql-spatial` (ST_Contains, ST_Difference) no
TruckFreightEasy, ao nível da aplicação em vez da base de dados.
"""

from shapely.geometry import Point, mapping, shape
from shapely.validation import make_valid


def _geometria_valida(geom):
    """
    Contornos vindos do Nominatim ocasionalmente têm auto-intersecções
    (ruído dos dados do OSM) - `shapely` recusa operações (contains,
    difference) em geometrias inválidas. `make_valid` corrige sem alterar
    visivelmente a forma.
    """
    return geom if geom.is_valid else make_valid(geom)


def ponto_dentro_poligono(lat, lng, geojson):
    """Testa se (lat, lng) cai dentro de um GeoJSON Polygon/MultiPolygon."""
    if not geojson:
        return False

    try:
        poligono = _geometria_valida(shape(geojson))
        return poligono.contains(Point(lng, lat))
    except Exception:
        return False


def bounds_do_poligono(geojson):
    """
    Rectângulo envolvente (bounding box) de um GeoJSON Polygon/MultiPolygon
    - só para estimar a área e desempatar entre polígonos sobrepostos.
    """
    oeste, sul, este, norte = shape(geojson).bounds
    return {"north": norte, "south": sul, "east": este, "west": oeste}


def recortar_sobreposicao(novo_geojson, geojsons_existentes):
    """
    Equivalente ao `resolveClippedMultiPolygon` do TruckFreightEasy: em vez
    de rejeitar uma zona nova que cruza com zonas já existentes, recorta
    (subtrai) as partes já cobertas - a zona nova fica só com a área que
    ainda não pertence a nenhuma outra. As zonas guardadas nunca se chegam
    a sobrepor.

    Devolve o GeoJSON já recortado, ou `None` se não sobrar nenhuma área
    (a forma pedida estava totalmente coberta por zonas existentes).
    """
    actual = _geometria_valida(shape(novo_geojson))

    for existente_geojson in geojsons_existentes:
        try:
            existente = _geometria_valida(shape(existente_geojson))
        except Exception:
            continue

        if not actual.intersects(existente):
            continue

        actual = actual.difference(existente)

        if actual.is_empty:
            return None

    return mapping(actual)
