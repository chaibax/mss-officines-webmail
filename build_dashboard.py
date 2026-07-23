#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Construit le « Tableau de bord — Pilotage MSS en officine » depuis out/agregats.json.

Design : DSFR (Système de Design de l'État) auto-hébergé (dashboard/dsfr/).
N'utilise que des dénombrements (aucune donnée nominative) → sûr à publier.

Deux modes :
  (défaut)  version publique : boutons de téléchargement CSV verrouillés (RGPD).
  --local   version interne  : copie les CSV dans dashboard/data/ et active les liens.

Usage : python3 build_dashboard.py [--local] [src=out/agregats.json] [dst=dashboard/index.html]
"""
import json
import os
import shutil
import sys

import email_logos
import france_map

GEOJSON = os.path.join(os.path.dirname(__file__), "assets", "departements-simplifie.geojson")

DEPT_NOMS = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Hte-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône",
    "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime",
    "18": "Cher", "19": "Corrèze", "20": "Corse", "21": "Côte-d'Or", "22": "Côtes-d'Armor",
    "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme", "27": "Eure",
    "28": "Eure-et-Loir", "29": "Finistère", "30": "Gard", "31": "Haute-Garonne",
    "32": "Gers", "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine", "36": "Indre",
    "37": "Indre-et-Loire", "38": "Isère", "39": "Jura", "40": "Landes", "41": "Loir-et-Cher",
    "42": "Loire", "43": "Haute-Loire", "44": "Loire-Atlantique", "45": "Loiret",
    "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère", "49": "Maine-et-Loire",
    "50": "Manche", "51": "Marne", "52": "Haute-Marne", "53": "Mayenne",
    "54": "Meurthe-et-Moselle", "55": "Meuse", "56": "Morbihan", "57": "Moselle",
    "58": "Nièvre", "59": "Nord", "60": "Oise", "61": "Orne", "62": "Pas-de-Calais",
    "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques", "65": "Hautes-Pyrénées",
    "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhône",
    "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie",
    "74": "Haute-Savoie", "75": "Paris", "76": "Seine-Maritime", "77": "Seine-et-Marne",
    "78": "Yvelines", "79": "Deux-Sèvres", "80": "Somme", "81": "Tarn",
    "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse", "85": "Vendée", "86": "Vienne",
    "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne", "90": "Terr. de Belfort",
    "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-St-Denis", "94": "Val-de-Marne",
    "95": "Val-d'Oise", "971": "Guadeloupe", "972": "Martinique", "973": "Guyane",
    "974": "La Réunion", "975": "St-Pierre-M.", "976": "Mayotte",
}
MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
BLEU, ROUGE = "#000091", "#e1000f"


def nf(x):
    return f"{int(x):,}".replace(",", " ")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def date_fr(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MOIS[int(m)]} {y}"


def hbar_svg(pairs, color=BLEU, bar_h=22, gap=8, label_w=210, val_w=60, width=880):
    maxv = max((v for _, v in pairs), default=1) or 1
    plot_w = width - label_w - val_w
    height = gap + len(pairs) * (bar_h + gap)
    parts = [f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" role="img">']
    for i, (lab, v) in enumerate(pairs):
        y = gap + i * (bar_h + gap)
        w = plot_w * v / maxv
        ty = y + bar_h * 0.70
        parts.append(f'<text class="hb-lab" x="{label_w - 9}" y="{ty:.1f}">{esc(lab)}</text>')
        parts.append(f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="4" fill="{color}"/>')
        parts.append(f'<text class="hb-val" x="{label_w + w + 7:.1f}" y="{ty:.1f}">{nf(v)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def logo_rows(pairs):
    maxv = max((c for _, c in pairs), default=1) or 1
    rows = []
    for dom, c in pairs:
        w = 100 * c / maxv
        rows.append(f"""<div class="drow">
        <div class="drow__logo">{email_logos.logo_svg(dom, 30)}</div>
        <div class="drow__name"><b>{esc(email_logos.label(dom))}</b><span>{esc(dom)}</span></div>
        <div class="drow__barwrap"><div class="drow__bar" style="width:{w:.1f}%"></div></div>
        <div class="drow__val">{nf(c)}</div>
      </div>""")
    return "\n".join(rows)


def funnel_html(steps):
    top = steps[0][1] or 1
    out = []
    for name, val, sub, color in steps:
        w = max(3, 100 * val / top)
        out.append(f"""<div class="step">
        <div class="step__name"><b>{esc(name)}</b><span>{esc(sub)}</span></div>
        <div class="step__barwrap"><div class="step__bar" style="width:{w:.1f}%;background:{color}"></div></div>
        <div class="step__val"><b style="color:{color}">{nf(val)}</b><span>{100 * val / top:.0f}&nbsp;% du parc</span></div>
      </div>""")
    return "\n".join(out)


def downloads_html(local, gp_lines, pro_lines):
    if local:
        return f"""<div class="fr-grid-row fr-grid-row--gutters">
        <div class="fr-col-12 fr-col-md-6"><div class="fr-download">
          <p><a href="data/officines_email_grand_public.csv" download class="fr-download__link">
            E-mails grand public (cibles)
            <span class="fr-download__detail">CSV — {gp_lines} lignes — séparateur «&nbsp;;&nbsp;»</span></a></p>
        </div></div>
        <div class="fr-col-12 fr-col-md-6"><div class="fr-download">
          <p><a href="data/officines_email_professionnel.csv" download class="fr-download__link">
            E-mails domaine propre («&nbsp;non public&nbsp;»)
            <span class="fr-download__detail">CSV — {pro_lines} lignes — séparateur «&nbsp;;&nbsp;»</span></a></p>
        </div></div>
      </div>
      <p class="fr-text--sm fr-mt-1w" style="color:var(--text-mention-grey)">Version interne — fichiers nominatifs présents localement.</p>"""
    return f"""<div class="fr-grid-row fr-grid-row--gutters">
      <div class="fr-col-12 fr-col-md-6"><div class="dl-locked">
        <span class="fr-icon-lock-line" aria-hidden="true"></span>
        <div><b>E-mails grand public — {gp_lines} lignes</b><span>Accès restreint (données personnelles). Disponible dans la version interne sécurisée.</span></div>
      </div></div>
      <div class="fr-col-12 fr-col-md-6"><div class="dl-locked">
        <span class="fr-icon-lock-line" aria-hidden="true"></span>
        <div><b>E-mails domaine propre — {pro_lines} lignes</b><span>Accès restreint (données personnelles). Disponible dans la version interne sécurisée.</span></div>
      </div></div>
    </div>"""


def build(agg, local=False):
    p = agg["parc"]
    d_iso = agg["date"]
    d_fr = date_fr(d_iso)
    pct_email = 100 * p["avec_email"] / p["officines"] if p["officines"] else 0

    cib = agg.get("cibles", {})
    a_equiper = cib.get("a_equiper", p["cibles_prioritaires"])
    a_accompagner = cib.get("a_accompagner", 0)

    steps = [
        ("Officines (pharmacies d'officine)", p["officines"], "répertoire FINESS type 620", BLEU),
        ("Avec e-mail déclaré", p["avec_email"], f"{pct_email:.0f} % du parc", "#6a6af4"),
        ("E-mail grand public", p["emails_grand_public"], "webmail / FAI", "#b34000"),
        ("Sans messagerie MSSanté → à équiper", a_equiper, "cible prioritaire", ROUGE),
    ]

    dom_rows = logo_rows(agg["top_domaines"][:12])
    dompro_svg = hbar_svg(agg.get("top_domaines_pro", [])[:12], color="#6a6af4", label_w=210, width=880)
    depts = agg["par_departement"][:15]
    dpairs = [(f'{DEPT_NOMS.get(r["dept"], r["dept"])} ({r["dept"]})', r["cibles"]) for r in depts]
    dept_svg = hbar_svg(dpairs, color=ROUGE, width=880, bar_h=22, gap=8, label_w=210)

    # Carte : densité d'e-mails grand public par département.
    vals = {r["dept"]: r["grand_public"] for r in agg["par_departement"]}
    carte_svg, legend = france_map.build_map(GEOJSON, vals, width=560)
    legend_html = "".join(
        f'<span class="leg"><i style="background:{c}"></i>{esc(l)}</span>' for c, l in legend)
    top3 = agg["par_departement"][:3]
    top3_html = " · ".join(
        f'<b>{esc(DEPT_NOMS.get(r["dept"], r["dept"]))}</b> {nf(r["grand_public"])}' for r in top3)

    non, oui = a_equiper, a_accompagner
    tot = oui + non or 1
    pna, poa = 100 * non / tot, 100 * oui / tot
    gpoff = nf(a_equiper + a_accompagner)

    return TEMPLATE.format(
        d_fr=esc(d_fr),
        officines=nf(p["officines"]), gp=nf(p["emails_grand_public"]), gpoff=gpoff,
        pro=nf(p["emails_professionnel"]), sans_email=nf(p["sans_email"]),
        avec_email=nf(p["avec_email"]), pct_email=f"{pct_email:.0f}",
        cibles=nf(a_equiper), accomp=nf(a_accompagner),
        kpi_pct_cible=f"{100 * a_equiper / p['officines']:.0f}" if p["officines"] else "0",
        funnel=funnel_html(steps), dom_rows=dom_rows, dompro_svg=dompro_svg, dept_svg=dept_svg,
        carte=carte_svg, legende=legend_html, top3=top3_html,
        non=nf(non), oui=nf(oui), pna=f"{pna:.0f}", poa=f"{poa:.0f}",
        n_depts=len(agg["par_departement"]),
        downloads=downloads_html(local, nf(p["lignes_grand_public"]), nf(p["lignes_professionnel"])),
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="fr" data-fr-scheme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tableau de bord — Pilotage MSS en officine</title>
<link rel="apple-touch-icon" href="dsfr/favicon/apple-touch-icon.png">
<link rel="icon" href="dsfr/favicon/favicon.svg" type="image/svg+xml">
<link rel="shortcut icon" href="dsfr/favicon/favicon.ico" type="image/x-icon">
<link rel="stylesheet" href="dsfr/utility/utility.min.css">
<link rel="stylesheet" href="dsfr/dsfr.min.css">
<style>
  .hero-badge{{margin-left:.5rem}}
  .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}}
  .stat{{background:var(--background-default-grey);border:1px solid var(--border-default-grey);border-bottom:4px solid var(--border-plain-blue-france);border-radius:.25rem;padding:1rem 1.1rem}}
  .stat.red{{border-bottom-color:var(--border-plain-red-marianne)}}
  .stat.blue{{border-bottom-color:var(--border-plain-blue-france)}}
  .stat__lab{{display:block;font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.02em;color:var(--text-mention-grey);min-height:2.4em}}
  .stat__big{{display:block;font-size:2rem;font-weight:800;line-height:1.05;font-variant-numeric:tabular-nums;margin:.15rem 0}}
  .stat.red .stat__big{{color:var(--text-default-error)}} .stat.blue .stat__big{{color:var(--text-active-blue-france)}}
  .stat__sub{{display:block;font-size:.8rem;color:var(--text-mention-grey);font-variant-numeric:tabular-nums}}
  .card{{background:var(--background-default-grey);border:1px solid var(--border-default-grey);border-radius:.25rem;padding:1.25rem 1.5rem;height:100%}}
  .card h2{{font-size:1.25rem;margin:0 0 .25rem}} .card .tag{{font-size:.85rem;color:var(--text-mention-grey);margin:0 0 1rem}}
  .step{{display:flex;align-items:center;gap:1rem;margin-bottom:.5rem}}
  .step__name{{flex:0 0 250px;font-size:.9rem}} .step__name b{{display:block}} .step__name span{{font-size:.78rem;color:var(--text-mention-grey)}}
  .step__barwrap{{flex:1;background:var(--background-contrast-grey);border-radius:5px;height:28px;overflow:hidden}}
  .step__bar{{height:100%;border-radius:5px}}
  .step__val{{flex:0 0 130px;text-align:right;font-variant-numeric:tabular-nums}} .step__val b{{font-size:1.15rem}} .step__val span{{display:block;font-size:.75rem;color:var(--text-mention-grey)}}
  .drow{{display:flex;align-items:center;gap:.85rem;padding:.35rem 0;border-bottom:1px solid var(--border-default-grey)}}
  .drow:last-child{{border-bottom:0}}
  .drow__name{{flex:0 0 190px;font-size:.9rem;line-height:1.15}} .drow__name b{{display:block}} .drow__name span{{font-size:.72rem;color:var(--text-mention-grey)}}
  .drow__barwrap{{flex:1;background:var(--background-contrast-grey);border-radius:5px;height:16px;overflow:hidden}}
  .drow__bar{{height:100%;background:var(--background-action-high-blue-france);border-radius:5px}}
  .drow__val{{flex:0 0 62px;text-align:right;font-weight:700;font-variant-numeric:tabular-nums}}
  svg.chart,.chart svg{{width:100%;height:auto;display:block}}
  .hb-lab{{fill:var(--text-default-grey);font-size:13px;text-anchor:end;font-family:Marianne,sans-serif}}
  .hb-val{{fill:var(--text-title-grey);font-size:13px;font-weight:700;text-anchor:start;font-variant-numeric:tabular-nums;font-family:Marianne,sans-serif}}
  .carte-wrap{{display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap}}
  .carte-fr{{flex:0 1 540px;max-width:540px;width:100%;height:auto}}
  .carte-side{{flex:1 1 240px;min-width:220px}}
  .leg{{display:flex;align-items:center;gap:.4rem;font-size:.82rem;margin:.25rem 0;font-variant-numeric:tabular-nums}}
  .leg i{{width:20px;height:14px;border-radius:3px;display:inline-block;border:1px solid rgba(0,0,0,.06)}}
  .split{{display:flex;height:60px;border-radius:.25rem;overflow:hidden;border:1px solid var(--border-default-grey)}}
  .split div{{display:flex;flex-direction:column;justify-content:center;padding:0 1rem;color:#fff;font-size:.82rem;line-height:1.3;white-space:nowrap;overflow:hidden}}
  .split .a{{background:var(--background-action-high-red-marianne)}} .split .b{{background:var(--background-action-high-blue-france)}}
  .split b{{font-size:.95rem;font-variant-numeric:tabular-nums}}
  .splitlab{{display:flex;justify-content:space-between;font-size:.75rem;color:var(--text-mention-grey);margin-top:.4rem}}
  .dl-locked{{display:flex;gap:.75rem;align-items:flex-start;background:var(--background-alt-grey);border:1px solid var(--border-default-grey);border-left:4px solid var(--border-plain-grey);border-radius:.25rem;padding:.85rem 1rem}}
  .dl-locked .fr-icon-lock-line{{color:var(--text-mention-grey)}} .dl-locked b{{display:block}} .dl-locked span{{font-size:.82rem;color:var(--text-mention-grey)}}
  @media(max-width:768px){{.stats{{grid-template-columns:repeat(2,1fr)}}.step__name{{flex-basis:130px}}.step__val{{flex-basis:96px}}.drow__name{{flex-basis:130px}}}}
</style>
</head>
<body>
<header role="banner" class="fr-header">
  <div class="fr-header__body">
    <div class="fr-container">
      <div class="fr-header__body-row">
        <div class="fr-header__brand fr-enlarge-link">
          <div class="fr-header__brand-top">
            <div class="fr-header__logo"><p class="fr-logo">République<br>Française</p></div>
          </div>
          <div class="fr-header__service">
            <a href="#" title="Tableau de bord — Pilotage MSS en officine">
              <p class="fr-header__service-title">Tableau de bord — Pilotage MSS en officine</p></a>
            <p class="fr-header__service-tagline">Direction du numérique en santé · adoption de la Messagerie Sécurisée de Santé</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</header>
<main id="contenu">
<div class="fr-container fr-my-4w">

  <div class="fr-callout fr-callout--brown-caramel fr-icon-dashboard-3-line">
    <h1 class="fr-callout__title">Pilotage de l'adoption MSSanté en officine
      <span class="fr-badge fr-badge--info fr-badge--no-icon hero-badge">Données au {d_fr}</span></h1>
    <p class="fr-callout__text">Sur <b>{officines}</b> pharmacies d'officine, <b>{gp}</b> affichent un e-mail de contact grand public. On en tire <b>deux cibles&nbsp;: {cibles} à équiper</b> (sans MSSanté) et <b>{accomp} à accompagner</b> (déjà équipées, joignables sur leur boîte grand public). Source&nbsp;: API FHIR Annuaire Santé (ANS), données publiques — sans scraping.</p>
  </div>

  <div class="stats fr-mb-4w">
    <div class="stat"><span class="stat__lab">Officines (type 620)</span><span class="stat__big">{officines}</span><span class="stat__sub">parc énuméré via l'API</span></div>
    <div class="stat"><span class="stat__lab">E-mails grand public</span><span class="stat__big">{gp}</span><span class="stat__sub">{pct_email}&nbsp;% des officines ont un e-mail</span></div>
    <div class="stat red"><span class="stat__lab">Cible 1 — à équiper</span><span class="stat__big">{cibles}</span><span class="stat__sub">grand public SANS MSSanté</span></div>
    <div class="stat blue"><span class="stat__lab">Cible 2 — à accompagner</span><span class="stat__big">{accomp}</span><span class="stat__sub">grand public AVEC MSSanté</span></div>
  </div>

  <div class="card fr-mb-3w">
    <h2>Répartition géographique — officines à e-mail grand public</h2>
    <p class="tag">Densité par département. Plus le bleu est foncé, plus il y a d'officines joignables en webmail grand public.</p>
    <div class="carte-wrap">
      {carte}
      <div class="carte-side">
        <p class="fr-text--sm fr-mb-1w"><b>Nombre d'officines à e-mail grand public</b></p>
        {legende}
        <hr class="fr-mt-2w fr-mb-2w">
        <p class="fr-text--sm" style="color:var(--text-mention-grey)">Top départements&nbsp;: {top3}</p>
      </div>
    </div>
  </div>

  <div class="card fr-mb-3w">
    <h2>Top domaines grand public</h2>
    <p class="tag">Fournisseurs des e-mails de contact déclarés par les officines.</p>
    {dom_rows}
  </div>

  <div class="fr-grid-row fr-grid-row--gutters fr-mb-3w">
    <div class="fr-col-12 fr-col-lg-6"><div class="card">
      <h2>L'entonnoir — du parc à la cible</h2>
      <p class="tag">Parc → e-mail → grand public → sans MSSanté (cible prioritaire).</p>
      {funnel}
    </div></div>
    <div class="fr-col-12 fr-col-lg-6"><div class="card">
      <h2>Deux cibles complémentaires</h2>
      <p class="tag">Répartition des {gpoff} officines à e-mail grand public.</p>
      <div class="split">
        <div class="a" style="flex:{pna}"><b>À équiper · {pna}&nbsp;%</b>{non} — sans MSSanté</div>
        <div class="b" style="flex:{poa}"><b>À accompagner · {poa}&nbsp;%</b>{oui} — déjà MSSanté</div>
      </div>
      <div class="splitlab"><span>↑ conversion prioritaire</span><span>déjà équipées, à activer ↑</span></div>
      <div class="fr-callout fr-callout--blue-ecume fr-mt-2w" style="padding:.85rem 1rem">
        <p class="fr-callout__text fr-text--sm"><b>Les «&nbsp;déjà équipées&nbsp;» restent une cible&nbsp;:</b> elles ont une BAL MSSanté mais affichent encore une boîte grand public — on peut les contacter dessus pour les accompagner vers un usage réel.</p>
      </div>
    </div></div>
  </div>

  <div class="fr-grid-row fr-grid-row--gutters fr-mb-3w">
    <div class="fr-col-12 fr-col-lg-6"><div class="card">
      <h2>Domaines professionnels («&nbsp;non public&nbsp;»)</h2>
      <p class="tag">Domaine propre (ni webmail, ni MSSanté)&nbsp;: {pro} e-mails. Surtout des plateformes logicielles/groupements officinaux. Contactables hors espace de confiance.</p>
      <div class="chart">{dompro_svg}</div>
    </div></div>
    <div class="fr-col-12 fr-col-lg-6"><div class="card">
      <h2>Cibles «&nbsp;à équiper&nbsp;» par département (top 15)</h2>
      <p class="tag">Officines grand public sans MSSanté, sur {n_depts} départements couverts.</p>
      <div class="chart">{dept_svg}</div>
    </div></div>
  </div>

  <div class="card fr-mb-3w">
    <h2>Exports pour action</h2>
    <p class="tag">Fichiers de campagne (séparateur «&nbsp;;&nbsp;», UTF-8). Données personnelles — usage strictement interne, finalité adoption MSSanté.</p>
    {downloads}
  </div>

  <div class="fr-accordions-group fr-mb-4w">
    <section class="fr-accordion">
      <h3 class="fr-accordion__title"><button class="fr-accordion__btn" aria-expanded="false" aria-controls="ac-methode">Méthode, périmètre &amp; RGPD</button></h3>
      <div class="fr-collapse" id="ac-methode">
        <p><b>Périmètre.</b> Toutes les <code>Organization</code> de type 620 (pharmacie d'officine) de l'Annuaire Santé, via l'API FHIR de l'ANS (données publiques). E-mail capté au niveau structure de l'officine.</p>
        <p><b>Deux cibles.</b> «&nbsp;À équiper&nbsp;» = grand public sans BAL MSSanté. «&nbsp;À accompagner&nbsp;» = grand public avec BAL MSSanté (équipée mais joignable hors espace de confiance). Équipement établi hors API, par croisement avec l'extraction quotidienne des BAL MSSanté (data.gouv.fr) et la présence d'une adresse <code>@*.mssante.fr</code>.</p>
        <p><b>Limite.</b> Le tier public ne couvre pas l'e-mail de correspondance des pharmacien·nes (donnée restreinte)&nbsp;: les {sans_email} officines sans e-mail public relèvent d'une extraction restreinte ou du lac BICOEUR.</p>
        <p><b>RGPD.</b> Cette page ne contient que des dénombrements agrégés — aucune donnée nominative. Les fichiers d'e-mails sont à usage interne (mission d'intérêt public, art.&nbsp;6.1.e + 6.3), finalité unique&nbsp;: adoption de MSSanté.</p>
      </div>
    </section>
  </div>
</div>
</main>
<footer class="fr-footer" role="contentinfo">
  <div class="fr-container">
    <div class="fr-footer__body">
      <div class="fr-footer__brand fr-enlarge-link">
        <p class="fr-logo">République<br>Française</p>
      </div>
      <div class="fr-footer__content">
        <p class="fr-footer__content-desc">Tableau de bord de pilotage de l'adoption MSSanté en officine. Fichier autonome, agrégats uniquement. Données&nbsp;: API FHIR Annuaire Santé (ANS), données publiques — extraction du {d_fr}.</p>
        <ul class="fr-footer__content-list">
          <li class="fr-footer__content-item"><a class="fr-footer__content-link" target="_blank" rel="noopener" href="https://github.com/chaibax/mss-officines-webmail">Code &amp; méthode (GitHub)</a></li>
          <li class="fr-footer__content-item"><a class="fr-footer__content-link" target="_blank" rel="noopener" href="https://esante.gouv.fr">esante.gouv.fr</a></li>
        </ul>
      </div>
    </div>
    <div class="fr-footer__bottom">
      <p class="fr-footer__bottom-copy">Sous licence — Direction du numérique en santé. Données personnelles traitées au titre d'une mission d'intérêt public (RGPD art. 6.1.e).</p>
    </div>
  </div>
</footer>
<script type="module" src="dsfr/dsfr.module.min.js"></script>
<script nomodule src="dsfr/dsfr.nomodule.min.js"></script>
</body>
</html>
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    local = "--local" in sys.argv
    src = args[0] if len(args) > 0 else "out/agregats.json"
    dst = args[1] if len(args) > 1 else "dashboard/index.html"
    with open(src, encoding="utf-8") as f:
        agg = json.load(f)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)

    if local:
        out_dir = os.path.dirname(src) or "out"
        data_dir = os.path.join(os.path.dirname(dst) or ".", "data")
        os.makedirs(data_dir, exist_ok=True)
        for name in ("officines_email_grand_public.csv", "officines_email_professionnel.csv"):
            srcf = os.path.join(out_dir, name)
            if os.path.exists(srcf):
                shutil.copy2(srcf, os.path.join(data_dir, name))
        print(f"Mode LOCAL : CSV copiés dans {data_dir}/ (ne pas déployer publiquement).")

    with open(dst, "w", encoding="utf-8") as f:
        f.write(build(agg, local=local))
    print(f"Dashboard écrit : {dst}" + (" (version interne, liens actifs)" if local else " (version publique, exports verrouillés)"))


if __name__ == "__main__":
    main()
