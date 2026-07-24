# -*- coding: utf-8 -*-
"""Carte choroplèthe de France (départements) en SVG, rendu serveur, sans JS.

Colorie chaque département selon le **taux** d'officines joignables via un
webmail grand public, rapporté au parc du département (grand_public / officines).
Un taux normalise la taille du département, contrairement à un volume brut.

Projection équirectangulaire calée sur la latitude moyenne de la France.
Géométrie : assets/departements-simplifie.geojson (open data, gregoiredavid/france-geojson).
"""
import json
import math

# Paliers en POURCENTAGE (seuil bas inclus) -> couleur, libellé de légende.
SCALE = [
    (0, "#e8e8fd", "moins de 10 %"),
    (10, "#cacafb", "10 – 24 %"),
    (25, "#a3a3f5", "25 – 39 %"),
    (40, "#8585f6", "40 – 54 %"),
    (55, "#4d4df0", "55 – 69 %"),
    (70, "#000091", "70 % et plus"),
]
SANS_DONNEE = "#eeeeee"
LAT0 = 46.6


def _color(pct):
    c = SCALE[0][1]
    for seuil, col, _ in SCALE:
        if pct >= seuil:
            c = col
    return c


def pct_fr(x, d=1):
    return f"{x:.{d}f}".replace(".", ",") + " %"


def _project_all(features):
    k = math.cos(math.radians(LAT0))
    xs, ys = [], []

    def pts(coords):
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
    def ring(r):
        d = ""
        for i, (lon, lat) in enumerate(r):
            d += ("M" if i == 0 else "L") + f"{tx(lon):.1f} {ty(lat):.1f} "
        return d + "Z "

    def walk(c, depth):
        if depth == 0:
            return ring(c)
        return "".join(walk(x, depth - 1) for x in c)

    depth = 1 if isinstance(coords[0][0][0], (int, float)) else 2
    return walk(coords, depth)


def build_map(geojson_path, data_by_dept, width=540):
    """data_by_dept : {code: {'pct': float, 'gp': int, 'tot': int, 'cov': float}}.

    Retourne (svg, legend) où legend = [(couleur, libellé), ...].
    """
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
             f'aria-label="Carte du taux d\'officines à e-mail grand public par département" '
             f'xmlns="http://www.w3.org/2000/svg" class="carte-fr">']
    for f in feats:
        code = f["properties"]["code"]
        nom = f["properties"]["nom"]
        rec = data_by_dept.get(code)
        if rec is None and code in ("2A", "2B"):   # Corse regroupée sous « 20 »
            rec = data_by_dept.get("20")
        d = _rings_to_path(f["geometry"]["coordinates"], tx, ty)
        if rec is None:
            fill, tip = SANS_DONNEE, f"{nom} ({code}) : donnée non disponible"
        else:
            fill = _color(rec["pct"])
            tip = (f"{nom} ({code}) : {pct_fr(rec['pct'])} d'officines à e-mail "
                   f"grand public ({rec['gp']} sur {rec['tot']}) — "
                   f"{pct_fr(rec['cov'], 0)} du parc déclare un e-mail")
        parts.append(f'<path d="{d}" fill="{fill}" stroke="#fff" stroke-width="0.6">'
                     f'<title>{tip}</title></path>')
    parts.append("</svg>")

    legend = [(col, lab) for _, col, lab in SCALE]
    return "".join(parts), legend
