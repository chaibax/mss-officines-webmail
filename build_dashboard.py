#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Construit le dashboard agrégé (fichier HTML autonome) depuis out/agregats.json.

N'utilise QUE des dénombrements (aucune donnée nominative) → sûr à publier.
Style DSFR, cohérent avec dashboard-penetration-mssante.html.

Usage : python3 build_dashboard.py [out/agregats.json] [dashboard/index.html]
"""
import json
import os
import sys

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
    "974": "La Réunion", "975": "St-Pierre-et-M.", "976": "Mayotte",
}

BLEU, BLEUCLAIR, ROUGE, VERT, AMBRE = "#000091", "#5b8def", "#e1000f", "#18753c", "#b34000"


def nf(x):
    return f"{int(x):,}".replace(",", " ")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hbar_svg(pairs, color=BLEU, fmt=nf, bar_h=24, gap=9, label_w=168, val_w=64, width=780):
    """Barres horizontales en SVG (rendu serveur, aucun JS)."""
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
        parts.append(f'<text class="hb-val" x="{label_w + w + 7:.1f}" y="{ty:.1f}">{esc(fmt(v))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def funnel_html(steps):
    top = steps[0][1] or 1
    out = []
    for name, val, sub, color in steps:
        w = max(3, 100 * val / top)
        pct = f"{100 * val / top:.0f} %"
        out.append(f"""<div class="step">
      <div class="name"><b>{esc(name)}</b><span>{esc(sub)}</span></div>
      <div class="barwrap"><div class="bar" style="width:{w:.1f}%;background:{color}"></div></div>
      <div class="pctbig"><b style="color:{color}">{nf(val)}</b><span>{pct} du parc</span></div>
    </div>""")
    return "\n".join(out)


def build(agg):
    p = agg["parc"]
    date = agg["date"]
    pct_email = 100 * p["avec_email"] / p["officines"] if p["officines"] else 0
    pct_cible = 100 * p["cibles_prioritaires"] / p["officines"] if p["officines"] else 0

    cib = agg.get("cibles", {})
    a_equiper = cib.get("a_equiper", p["cibles_prioritaires"])
    a_accompagner = cib.get("a_accompagner", 0)

    steps = [
        ("Officines (pharmacies d'officine)", p["officines"],
         "répertoire FINESS type 620", BLEU),
        ("Avec e-mail déclaré", p["avec_email"],
         f"{pct_email:.0f} % du parc — donnée publique", BLEUCLAIR),
        ("E-mail grand public", p["emails_grand_public"],
         "webmail / FAI (gmail, orange...)", AMBRE),
        ("Sans messagerie MSSanté → à équiper", a_equiper,
         "grand public ET aucune BAL MSSanté", ROUGE),
    ]

    dom_svg = hbar_svg(agg["top_domaines"][:12], color=BLEU)
    dompro_svg = hbar_svg(agg.get("top_domaines_pro", [])[:12], color=BLEUCLAIR)

    depts = agg["par_departement"][:20]
    dpairs = [(f'{DEPT_NOMS.get(r["dept"], r["dept"])} ({r["dept"]})', r["cibles"]) for r in depts]
    dept_svg = hbar_svg(dpairs, color=ROUGE, width=780, bar_h=22, gap=8, label_w=210)

    # Répartition en OFFICINES distinctes (cohérent avec KPI et bannière).
    non, oui = a_equiper, a_accompagner
    tot = oui + non or 1
    pna, poa = 100 * non / tot, 100 * oui / tot
    gpoff = nf(a_equiper + a_accompagner)

    kpi = f"""<div class="kpis">
    <div class="kpi"><div class="lab">Officines (type 620)</div>
      <div class="big">{nf(p['officines'])}</div><div class="small">parc énuméré via l'API</div></div>
    <div class="kpi"><div class="lab">E-mails grand public</div>
      <div class="big">{nf(p['emails_grand_public'])}</div><div class="small">{pct_email:.0f} % des officines ont un e-mail</div></div>
    <div class="kpi hero"><div class="lab">Cible 1 &mdash; à équiper</div>
      <div class="big">{nf(a_equiper)}</div><div class="small">grand public SANS MSSanté</div></div>
    <div class="kpi accomp"><div class="lab">Cible 2 &mdash; à accompagner</div>
      <div class="big">{nf(a_accompagner)}</div><div class="small">grand public AVEC MSSanté</div></div>
  </div>"""

    return TEMPLATE.format(
        date=esc(date), officines=nf(p["officines"]),
        cibles=nf(a_equiper), accomp=nf(a_accompagner), gp=nf(p["emails_grand_public"]),
        pro=nf(p["emails_professionnel"]), lignes_pro=nf(p.get("lignes_professionnel", 0)),
        sans_email=nf(p["sans_email"]), pct_cible=f"{pct_cible:.0f}",
        kpi=kpi, funnel=funnel_html(steps), dom_svg=dom_svg, dompro_svg=dompro_svg,
        dept_svg=dept_svg, oui=nf(oui), non=nf(non), gpoff=gpoff,
        pna=f"{pna:.0f}", poa=f"{poa:.0f}",
        n_depts=len(agg["par_departement"]),
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Officines à e-mail grand public — cibles d'adoption MSSanté</title>
<style>
  :root{{
    --bleu:#000091;--bleu-clair:#5b8def;--bleu-pale2:#f2f2ff;--rouge:#e1000f;--vert:#18753c;--ambre:#b34000;
    --encre:#161616;--gris:#666;--gris-clair:#e5e5e5;--fond:#f6f6fb;--carte:#fff;
    --ombre:0 1px 3px rgba(0,0,18,.08),0 6px 24px rgba(0,0,18,.05);--radius:12px;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--fond);color:var(--encre);font-size:16px;line-height:1.45;
    font-family:"Marianne","Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif}}
  .wrap{{max-width:1120px;margin:0 auto;padding:0 20px 70px}}
  header.top{{max-width:1120px;margin:0 auto;padding:28px 20px 6px}}
  .eyebrow{{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;
    letter-spacing:.04em;text-transform:uppercase;color:var(--rouge);background:#ffe9e9;padding:5px 12px;border-radius:99px}}
  h1{{font-size:28px;line-height:1.14;margin:13px 0 6px;font-weight:800;letter-spacing:-.01em}}
  .sub{{color:var(--gris);max-width:860px;margin:0;font-size:15.5px}}
  .ref-badge{{display:inline-block;margin-top:10px;font-size:12.5px;color:var(--gris);border:1px solid var(--gris-clair);border-radius:8px;padding:4px 10px;background:#fff}}
  .banner{{background:linear-gradient(135deg,#11114a,#000091);color:#fff;border-radius:var(--radius);padding:20px 24px;margin:22px 0 20px;box-shadow:var(--ombre);font-size:16.5px;line-height:1.55}}
  .banner .em{{color:#ff9a9a;font-weight:800}}.banner .em2{{color:#a9c4ff;font-weight:800}}.banner b{{color:#fff}}.banner .huge{{font-size:21px;font-weight:800;display:block;margin-bottom:6px}}
  .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}}
  .kpi{{background:var(--carte);border:1px solid var(--gris-clair);border-radius:var(--radius);padding:15px 17px;box-shadow:var(--ombre)}}
  .kpi .lab{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.02em;color:var(--gris);margin-bottom:7px;min-height:30px}}
  .kpi .big{{font-size:29px;font-weight:800;line-height:1.05;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
  .kpi .small{{font-size:12.5px;color:var(--gris);margin-top:6px;font-variant-numeric:tabular-nums}}
  .kpi.hero .big{{color:var(--rouge)}} .kpi.accomp .big{{color:var(--bleu)}}
  .panel{{background:var(--carte);border:1px solid var(--gris-clair);border-radius:var(--radius);padding:20px 22px;box-shadow:var(--ombre);margin-bottom:20px}}
  .panel h2{{font-size:18px;margin:0 0 4px}}.panel .ptag{{font-size:13px;color:var(--gris);margin:0 0 16px}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
  .step{{display:flex;align-items:center;gap:14px;padding:10px 12px;border-radius:10px;margin-bottom:8px}}
  .step .name{{flex:0 0 250px;font-size:14px}}
  .step .name b{{display:block}} .step .name span{{font-size:12px;color:var(--gris);font-variant-numeric:tabular-nums}}
  .step .barwrap{{flex:1;background:#f0f0f5;border-radius:6px;height:30px;overflow:hidden}}
  .step .bar{{height:100%;border-radius:6px}}
  .step .pctbig{{flex:0 0 150px;text-align:right;font-variant-numeric:tabular-nums}}
  .step .pctbig b{{font-size:20px;font-weight:800}} .step .pctbig span{{font-size:12px;color:var(--gris);display:block}}
  svg{{width:100%;height:auto;display:block}}
  .hb-lab{{fill:#333;font-size:13px;text-anchor:end;font-family:inherit}}
  .hb-val{{fill:#111;font-size:13px;font-weight:700;text-anchor:start;font-variant-numeric:tabular-nums;font-family:inherit}}
  .split{{display:flex;height:58px;border-radius:8px;overflow:hidden;border:1px solid var(--gris-clair)}}
  .split div{{display:flex;flex-direction:column;justify-content:center;padding:0 15px;color:#fff;font-size:12.5px;line-height:1.3;white-space:nowrap;overflow:hidden}}
  .split .a{{background:var(--rouge)}} .split .b{{background:var(--bleu)}}
  .split b{{font-size:14px;font-variant-numeric:tabular-nums}}
  .splitlab{{display:flex;justify-content:space-between;font-size:11.5px;color:var(--gris);margin-top:7px}}
  .note{{font-size:13px;color:#333;background:var(--bleu-pale2);border-radius:8px;padding:11px 14px;margin-top:14px;line-height:1.5}}
  details.method{{margin-top:6px;background:var(--carte);border:1px solid var(--gris-clair);border-radius:var(--radius);padding:16px 20px;box-shadow:var(--ombre)}}
  details.method summary{{cursor:pointer;font-weight:700;color:var(--bleu);font-size:15px}}
  details.method .body{{font-size:13.5px;color:#333;margin-top:12px}}
  details.method code{{background:var(--bleu-pale2);padding:1px 6px;border-radius:5px}}
  footer{{max-width:1120px;margin:22px auto 0;padding:0 20px;font-size:12.5px;color:var(--gris)}}
  footer a{{color:var(--bleu)}}
  @media(max-width:880px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.grid2{{grid-template-columns:1fr}}.step .name{{flex-basis:150px}}.step .pctbig{{flex-basis:110px}}h1{{font-size:22px}}}}
</style>
</head>
<body>
<header class="top">
  <span class="eyebrow">● MSSanté — DNS · cibles d'adoption</span>
  <h1>Officines joignables en webmail « grand public » : {cibles} à équiper, {accomp} à accompagner</h1>
  <p class="sub">Une adresse de contact en webmail grand public (gmail, orange…) est un marqueur de maturité numérique. Croisée avec la messagerie MSSanté, elle dessine deux cibles complémentaires. Données de l'<b>Annuaire Santé</b> (ANS), tier public, sans scraping.</p>
  <div class="ref-badge">Source : API FHIR Annuaire Santé (ANS), données publiques · extraction du {date} · {officines} officines énumérées</div>
</header>
<div class="wrap">
  <div class="banner">
    <span class="huge">Deux cibles, une même porte d'entrée : la boîte grand public.</span>
    Sur {officines} pharmacies d'officine, <b>{gp} affichent un e-mail de contact grand public</b>. Parmi elles, <span class="em">{cibles} n'ont aucune messagerie MSSanté</span> (à équiper) et <span class="em2">{accomp} en ont déjà une</span> (déjà équipées, à accompagner vers l'usage) — toutes joignables directement sur leur boîte grand public. En complément, {sans_email} officines ne déclarent aucun e-mail public : à traiter en donnée restreinte ou via BICOEUR.
  </div>
  {kpi}
  <div class="panel">
    <h2>L'entonnoir — du parc à la cible « à équiper »</h2>
    <p class="ptag">Parc total → officines avec e-mail → e-mail grand public → sans messagerie MSSanté. La dernière barre est la cible prioritaire de conversion.</p>
    {funnel}
  </div>
  <div class="grid2">
    <div class="panel">
      <h2>Top domaines grand public</h2>
      <p class="ptag">Domaines des e-mails de contact déclarés par les officines.</p>
      {dom_svg}
    </div>
    <div class="panel">
      <h2>Deux cibles complémentaires</h2>
      <p class="ptag">Répartition des {gpoff} officines à e-mail grand public : sans MSSanté (à équiper) vs. déjà équipée (à accompagner).</p>
      <div class="split">
        <div class="a" style="flex:{pna}"><b>À équiper · {pna}&nbsp;%</b>{non} — sans MSSanté</div>
        <div class="b" style="flex:{poa}"><b>À accompagner · {poa}&nbsp;%</b>{oui} — déjà MSSanté</div>
      </div>
      <div class="splitlab"><span>↑ conversion prioritaire</span><span>déjà équipées, à activer ↑</span></div>
      <div class="note"><b>Les « déjà équipées » restent une cible.</b> Elles ont une BAL MSSanté mais continuent d'afficher une boîte grand public : signe qu'elles n'ont pas basculé leurs usages. On peut les contacter sur cette boîte grand public pour les accompagner vers un usage réel de MSSanté.</div>
    </div>
  </div>
  <div class="panel">
    <h2>Domaines professionnels (domaine propre — « non public »)</h2>
    <p class="ptag">Officines à e-mail sur domaine propre (ni webmail, ni MSSanté) : {pro} e-mails distincts. Contactables hors espace de confiance. Le top révèle surtout des plateformes de logiciels/groupements officinaux.</p>
    {dompro_svg}
    <div class="note">Export dédié disponible : <code>officines_email_professionnel.csv</code> ({lignes_pro} lignes) — hors ligne (donnée personnelle), pour un contact direct sans passer par l'espace de confiance MSSanté.</div>
  </div>
  <div class="panel">
    <h2>Cibles « à équiper » par département (top 20)</h2>
    <p class="ptag">Officines à e-mail grand public sans messagerie MSSanté, par département — sur {n_depts} départements couverts. De quoi prioriser géographiquement une campagne.</p>
    {dept_svg}
  </div>
  <details class="method" open>
    <summary>Méthode, périmètre &amp; RGPD</summary>
    <div class="body">
      <p><b>Périmètre.</b> Toutes les <code>Organization</code> de type 620 (pharmacie d'officine) de l'Annuaire Santé, énumérées via l'API FHIR de l'ANS (données publiques). L'e-mail capté est celui déclaré au niveau <i>structure</i> de l'officine.</p>
      <p><b>Classification.</b> Le domaine après « @ » est classé <code>grand public</code> (webmail/FAI), <code>professionnel</code> (domaine propre, « non public ») ou <code>MSSanté</code> (<code>@*.mssante.fr</code>, non exporté car déjà dans l'espace de confiance).</p>
      <p><b>Deux cibles grand public.</b> <b>À équiper</b> = e-mail grand public ET aucune BAL MSSanté. <b>À accompagner</b> = e-mail grand public ET BAL MSSanté existante (équipée mais joignable hors trust space). L'équipement MSSanté est établi hors API, par croisement avec l'extraction quotidienne des BAL MSSanté (data.gouv.fr) et la présence d'une adresse <code>@*.mssante.fr</code>.</p>
      <p><b>Limite.</b> Le tier public ne couvre pas l'e-mail de correspondance des pharmacien·nes (donnée restreinte) : les {sans_email} officines sans e-mail public relèvent d'une extraction restreinte ou du lac BICOEUR.</p>
      <p><b>RGPD.</b> Cette page ne contient que des <b>dénombrements agrégés</b> — aucune adresse, aucun nom, aucun FINESS individuel. Les fichiers nominatifs de campagne restent hors ligne. Traitement fondé sur une mission d'intérêt public (art. 6.1.e + 6.3), finalité unique = adoption de MSSanté.</p>
    </div>
  </details>
</div>
<footer>
  Fichier autonome, agrégats uniquement. Code &amp; méthode :
  <a href="https://github.com/chaibax/mss-officines-webmail">github.com/chaibax/mss-officines-webmail</a>.
  Source : API FHIR Annuaire Santé (ANS), données publiques — extraction du {date}.
</footer>
</body>
</html>
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "out/agregats.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "dashboard/index.html"
    with open(src, encoding="utf-8") as f:
        agg = json.load(f)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(build(agg))
    print(f"Dashboard écrit : {dst}")


if __name__ == "__main__":
    main()
