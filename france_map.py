# -*- coding: utf-8 -*-
"""Carte choroplèthe de France (départements) en SVG, rendu serveur, sans JS.

Colorie chaque département selon une valeur (ici : nombre d'officines à e-mail
grand public). Projection simple « équirectangulaire » calée sur la latitude
moyenne de la France — suffisante pour une carte de pilotage lisible.
Géométrie : assets/departements-simplifie.geojson (open data, gregoiredavid/france-geojson).
"""
import json
import math

# Échelle séquentielle bleue DSFR (clair -> Bleu France).
SCALE = [
    (0, "#eeeeee"),      # 0
    (1, "#e3e3fd"),      # 1-24
    (25, "#cacafb"),     # 25-74
    (75, "#8585f6"),     # 75-149
    (150, "#6a6af4"),    # 150-299
    (300, "#000091"),    # 300+
]
LAT0 = 46.6


def _color(v):
    c = SCALE[0][1]
    for seuil, col in SCALE:
        if v >= seuil:
            c = col
    return c


def _project_all(features):
    k = math.cos(math.radians(LAT0))
    xs, ys = [], []

    def pts(coords):
        # descend jusqu'aux paires [lon, lat]
        if coords and isinstance(coords[0], (int, float)):
            xs.append(coords[0] * k)
            ys.append(-coords[1])
        else:
            for c in coords:
                pts(c)
    for f in features:
        pts(f["geometry"]["coordinates"])
    return min(xs), max(xs), min(ys), max(ys), k


def _rings_to_path(coords, tx, ty):
    """Convertit Polygon/MultiPolygon en 'd' SVG."""
    out = []

    def ring(r):
        d = ""
        for i, (lon, lat) in enumerate(r):
            x, y = tx(lon), ty(lat)
            d += ("M" if i == 0 else "L") + f"{x:.1f} {y:.1f} "
        return d + "Z "

    def walk(c, depth):
        # Polygon: [ring, ...] ; MultiPolygon: [[ring,...], ...]
        if depth == 0:
            # c is a ring (list of [lon,lat])
            return ring(c)
        return "".join(walk(x, depth - 1) for x in c)

    geomtype_depth = 1 if isinstance(coords[0][0][0], (int, float)) else 2
    return walk(coords, geomtype_depth)


def build_map(geojson_path, value_by_dept, width=560, id_prefix="fr"):
    """Retourne (svg, legend_items). value_by_dept: {code_dept: valeur}."""
    g = json.load(open(geojson_path, encoding="utf-8"))
    feats = g["features"]
    minx, maxx, miny, maxy, k = _project_all(feats)
    pad = 6
    scale = (width - 2 * pad) / (maxx - minx)
    height = (maxy - miny) * scale + 2 * pad

    def tx(lon):
        return pad + (lon * k - minx) * scale

    def ty(lat):
        return pad + (-lat - miny) * scale

    parts = [f'<svg viewBox="0 0 {width} {height:.0f}" role="img" '
             f'aria-label="Carte des officines à e-mail grand public par département" '
             f'xmlns="http://www.w3.org/2000/svg" class="carte-fr">']
    for f in feats:
        code = f["properties"]["code"]
        nom = f["properties"]["nom"]
        # Corse 2A/2B rattachée au comptage "20".
        v = value_by_dept.get(code)
        if v is None and code in ("2A", "2B"):
            v = value_by_dept.get("20", 0)
        v = v or 0
        d = _rings_to_path(f["geometry"]["coordinates"], tx, ty)
        parts.append(f'<path d="{d}" fill="{_color(v)}" stroke="#fff" '
                     f'stroke-width="0.6"><title>{nom} ({code}) : {v} officines</title></path>')
    parts.append("</svg>")

    legend = []
    labels = ["0", "1–24", "25–74", "75–149", "150–299", "300 +"]
    for (_, col), lab in zip(SCALE, labels):
        legend.append((col, lab))
    return "".join(parts), legend
