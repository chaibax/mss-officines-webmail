#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extraction des officines joignables via une adresse e-mail « grand public ».

Objectif (cf. brief) : constituer une liste ciblée d'officines dont l'e-mail de
contact relève d'un webmail grand public (gmail.com et équivalents), marqueur de
faible maturité numérique et cible prioritaire d'adoption MSSanté. Source unique :
API FHIR Annuaire Santé (ANS). Aucun scraping.

Séquence :
  (A) énumérer les officines (donnée publique : Organization type=620) ;
  (B) si clé « données restreintes » : e-mail de correspondance des pharmaciens ;
  (enrichissement) croiser avec l'équipement MSSanté depuis l'extraction locale ;
  (sortie) normaliser, filtrer les domaines grand public, produire CSV + synthèse.

Usage :
  export ANS_API_KEY="…"                     # clé portail.openfhir.annuaire.sante.fr
  python3 extract_officines.py --probe       # 1er run : valide clé, params, échantillon
  python3 extract_officines.py               # voie A (public) + enrichissement + sorties
  python3 extract_officines.py --restreint   # + voie B (requiert habilitation DR)
  python3 extract_officines.py --limit 200   # test rapide sur un échantillon

Sorties (dans --out, défaut ./out) :
  officines_email_grand_public.csv ; synthese.md
"""
import argparse
import csv
import os
import sys
from collections import Counter
from datetime import date

import bal_index
import classify
import config
from ans_client import AnnuaireClient, AnnuaireError

CSV_COLUMNS = [
    "finess", "raison_sociale", "adresse", "code_postal", "ville",
    "rpps", "nom", "prenom", "email", "domaine", "categorie_domaine",
    "a_bal_mss", "source",
]
SRC_PUBLIC = "organization_public"
SRC_RESTREINT = "practitioner_restreint"


# ------------------------------------------------------------- parsing FHIR
def telecom_emails(resource):
    """Valeurs brutes des telecom de system=email."""
    out = []
    for t in resource.get("telecom", []) or []:
        if t.get("system") == "email" and t.get("value"):
            out.append(t["value"])
    return out


def classified_emails(resource):
    """[(email, domaine, categorie)] normalisés et classés pour une ressource."""
    result = []
    for raw in telecom_emails(resource):
        norm = classify.normalize_email(raw)
        if not norm:
            continue
        email, domain = norm
        result.append((email, domain, classify.classify_domain(domain)))
    return result


def pick_finess(org):
    """FINESS de l'officine parmi les identifiants (repli : 1er identifiant)."""
    ids = org.get("identifier", []) or []
    for ident in ids:
        system = (ident.get("system") or "").lower()
        if "finess" in system and ident.get("value"):
            return ident["value"].strip()
    for ident in ids:
        val = (ident.get("value") or "").strip()
        if val.isdigit() and len(val) == 9:
            return val
    return (ids[0].get("value", "").strip() if ids else "")


def pick_address(org):
    """(adresse, code_postal, ville) depuis la 1re adresse."""
    addrs = org.get("address", []) or []
    if not addrs:
        return "", "", ""
    a = addrs[0]
    line = " ".join(a.get("line", []) or []).strip()
    return line, (a.get("postalCode") or "").strip(), (a.get("city") or "").strip()


def practitioner_name(pract):
    """(nom, prenom) depuis le 1er name."""
    names = pract.get("name", []) or []
    if not names:
        return "", ""
    n = names[0]
    given = " ".join(n.get("given", []) or []).strip()
    return (n.get("family") or "").strip(), given


def pick_rpps(pract):
    ids = pract.get("identifier", []) or []
    for ident in ids:
        system = (ident.get("system") or "").lower()
        if ("rpps" in system or "idnps" in system) and ident.get("value"):
            return ident["value"].strip()
    return (ids[0].get("value", "").strip() if ids else "")


# ------------------------------------------------------------- énumération
def enumerate_officines(client, limit=None):
    """Voie A : Organization type=620, avec repli sur le token system|code."""
    base_params = {"_count": config.PAGE_SIZE}
    attempts = [
        {**base_params, "type": config.OFFICINE_TYPE_CODE},
        {**base_params, "type": f"{config.OFFICINE_TYPE_SYSTEM}|{config.OFFICINE_TYPE_CODE}"},
    ]
    last_err = None
    for params in attempts:
        try:
            count = 0
            for org in client.search_resources("Organization", params):
                yield org
                count += 1
                if limit and count >= limit:
                    return
            return
        except AnnuaireError as e:
            last_err = e
            print(f"  [voieA] token type refusé, tentative suivante… ({e})",
                  file=sys.stderr)
    raise last_err


def pharmaciens_of(client, org_id):
    """Voie B : PractitionerRole de l'officine + Practitioner inclus.

    Renvoie des couples (practitioner_role, practitioner). On n'impose pas de
    valeur `use` sur le telecom : la sélection grand_public se fait en aval.
    """
    params = {
        "organization": org_id,
        "_include": "PractitionerRole:practitioner",
        "_count": config.PAGE_SIZE,
    }
    for bundle in client.search_pages("PractitionerRole", params):
        practitioners = {}
        roles = []
        for entry in bundle.get("entry", []) or []:
            res = entry.get("resource") or {}
            rtype = res.get("resourceType")
            if rtype == "Practitioner":
                practitioners[f"Practitioner/{res.get('id')}"] = res
            elif rtype == "PractitionerRole":
                roles.append(res)
        for role in roles:
            ref = (role.get("practitioner") or {}).get("reference", "")
            yield role, practitioners.get(ref, {})


# ------------------------------------------------------------------- probe
def probe(client):
    """1er run recommandé : valide la clé, liste les search params, échantillonne."""
    print("== CapabilityStatement (/metadata) ==")
    meta = client.metadata()
    print(f"  logiciel : {meta.get('software', {}).get('name', '?')} "
          f"{meta.get('software', {}).get('version', '')}")
    print(f"  FHIR     : {meta.get('fhirVersion', '?')}")
    wanted = {"Organization", "Practitioner", "PractitionerRole"}
    for rest in meta.get("rest", []) or []:
        for res in rest.get("resource", []) or []:
            if res.get("type") in wanted:
                params = sorted(sp.get("name") for sp in res.get("searchParam", []) or [])
                print(f"  {res['type']:16} params: {', '.join(params) or '(aucun listé)'}")
    print("\n== Échantillon Organization type=620 (1 officine) ==")
    sample = None
    for org in enumerate_officines(client, limit=1):
        sample = org
    if not sample:
        print("  Aucune officine renvoyée. Vérifier le code type / le périmètre de la clé.")
        return
    finess = pick_finess(sample)
    line, cp, ville = pick_address(sample)
    tel_systems = Counter((t.get("system") or "?") for t in sample.get("telecom", []) or [])
    print(f"  FINESS         : {finess}")
    print(f"  raison sociale : {sample.get('name', '')}")
    print(f"  adresse        : {line} {cp} {ville}".strip())
    print(f"  telecom        : {dict(tel_systems) or '(aucun)'}")
    emails = classified_emails(sample)
    if emails:
        for email, domain, cat in emails:
            print(f"    e-mail structure : {email}  [{cat}]")
    else:
        print("    (aucun e-mail au niveau structure — attendu : l'e-mail est "
              "surtout en donnée restreinte, voir voie B)")
    print("\nProbe terminé. Si des e-mails de structure apparaissent, la voie A "
          "produira des lignes ; sinon l'essentiel du gisement est en voie B (DR).")


# ---------------------------------------------------------------- extraction
def run(args):
    client = AnnuaireClient(verbose=True)

    # Enrichissement MSSanté (hors API) depuis l'extraction locale.
    bal = bal_index.BalIndex.empty()
    if not args.no_bal:
        path = bal_index.find_extraction(args.bal)
        if path:
            bal = bal_index.BalIndex.from_file(path)
        else:
            print("  [bal] extraction MSSanté introuvable : a_bal_mss = 'inconnu'. "
                  "Télécharger le fichier data.gouv.fr ou passer --bal CHEMIN.",
                  file=sys.stderr)

    rows = []
    seen = set()                     # dédoublonnage (finess, email)
    n_officines = 0
    n_officines_email_public = 0     # officines déclarant ≥1 e-mail de structure
    emails_par_cat = {config.CAT_GRAND_PUBLIC: set(),
                      config.CAT_PRO: set(),
                      config.CAT_MSSANTE: set()}
    top_domaines = Counter()
    cibles_finess = set()            # officines grand_public sans BAL MSS

    def a_bal_value(has):
        return "inconnu" if not bal.available else ("oui" if has else "non")

    for org in enumerate_officines(client, limit=args.limit):
        n_officines += 1
        finess = pick_finess(org)
        name = org.get("name", "")
        line, cp, ville = pick_address(org)
        org_emails = classified_emails(org)
        if org_emails:
            n_officines_email_public += 1
        officine_bal = bal.officine_has_bal(finess)

        # Voie A — e-mails déclarés au niveau structure.
        for email, domain, cat in org_emails:
            emails_par_cat[cat].add(email)
            if cat != config.CAT_GRAND_PUBLIC:
                continue
            key = (finess, email)
            if key in seen:
                continue
            seen.add(key)
            top_domaines[domain] += 1
            rows.append({
                "finess": finess, "raison_sociale": name, "adresse": line,
                "code_postal": cp, "ville": ville, "rpps": "", "nom": "", "prenom": "",
                "email": email, "domaine": domain, "categorie_domaine": cat,
                "a_bal_mss": a_bal_value(officine_bal), "source": SRC_PUBLIC,
            })
            if bal.available and not officine_bal:
                cibles_finess.add(finess)

        # Voie B — e-mail de correspondance des pharmaciens (donnée restreinte).
        if args.restreint and finess:
            org_id = org.get("id")
            if not org_id:
                continue
            for role, pract in pharmaciens_of(client, org_id):
                if not pract:
                    continue
                rpps = pick_rpps(pract)
                nom, prenom = practitioner_name(pract)
                pharm_bal = bal.pharmacien_has_bal(rpps) or officine_bal
                for email, domain, cat in classified_emails(pract):
                    emails_par_cat[cat].add(email)
                    if cat != config.CAT_GRAND_PUBLIC:
                        continue
                    key = (finess, email)
                    if key in seen:
                        continue
                    seen.add(key)
                    top_domaines[domain] += 1
                    rows.append({
                        "finess": finess, "raison_sociale": name, "adresse": line,
                        "code_postal": cp, "ville": ville, "rpps": rpps,
                        "nom": nom, "prenom": prenom, "email": email,
                        "domaine": domain, "categorie_domaine": cat,
                        "a_bal_mss": a_bal_value(pharm_bal), "source": SRC_RESTREINT,
                    })
                    if bal.available and not pharm_bal:
                        cibles_finess.add(finess)

        if n_officines % 1000 == 0:
            print(f"  [progress] {n_officines} officines, {len(rows)} lignes "
                  f"grand public", file=sys.stderr)

    write_outputs(args.out, rows, {
        "n_officines": n_officines,
        "n_officines_email_public": n_officines_email_public,
        "emails_par_cat": {k: len(v) for k, v in emails_par_cat.items()},
        "top_domaines": top_domaines,
        "n_cibles": len(cibles_finess),
        "bal_available": bal.available,
        "restreint": args.restreint,
    })


# -------------------------------------------------------------------- sorties
def write_outputs(out_dir, rows, stats):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "officines_email_grand_public.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["code_postal"], r["finess"], r["email"])):
            w.writerow(r)

    md_path = os.path.join(out_dir, "synthese.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(build_synthese(rows, stats))

    print(f"\nÉcrit : {csv_path} ({len(rows)} lignes) ; {md_path}")


def build_synthese(rows, stats):
    tag = date.today().strftime("%Y-%m-%d")
    n = stats["n_officines"]
    n_email = stats["n_officines_email_public"]
    cat = stats["emails_par_cat"]
    sans_email = n - n_email
    pct_email = f"{n_email / n:.1%}" if n else "—"
    a_bal_note = ("croisé avec l'extraction MSSanté locale"
                  if stats["bal_available"] else "extraction MSSanté absente → a_bal_mss='inconnu'")

    lines = [
        f"# Synthèse — Officines à e-mail grand public ({tag})",
        "",
        f"Source : API FHIR Annuaire Santé (ANS). Voie B (donnée restreinte) "
        f"{'activée' if stats['restreint'] else 'non activée'}. Enrichissement : {a_bal_note}.",
        "",
        "## Volumétrie",
        "",
        "| Indicateur | Valeur |",
        "|---|---:|",
        f"| Officines énumérées (type 620) | {n:,} |",
        f"| Officines avec ≥1 e-mail déclaré | {n_email:,} ({pct_email}) |",
        f"| Officines sans e-mail public | {sans_email:,} |",
        f"| E-mails distincts — grand public | {cat[config.CAT_GRAND_PUBLIC]:,} |",
        f"| E-mails distincts — professionnel | {cat[config.CAT_PRO]:,} |",
        f"| E-mails distincts — MSSanté | {cat[config.CAT_MSSANTE]:,} |",
        f"| **Lignes grand public retenues (CSV)** | **{len(rows):,}** |",
        f"| **Cibles prioritaires (grand public SANS BAL MSSanté)** | **{stats['n_cibles']:,}** |",
        "",
        "## Top domaines grand public",
        "",
        "| Domaine | Occurrences |",
        "|---|---:|",
    ]
    for domain, count in stats["top_domaines"].most_common(15):
        lines.append(f"| {domain} | {count:,} |")

    lines += [
        "",
        "## Écart d'habilitation",
        "",
    ]
    if not stats["restreint"]:
        lines.append(
            f"Exécution en **donnée publique** : seuls les e-mails déclarés au niveau "
            f"*structure* de l'officine sont captés. L'e-mail de correspondance des "
            f"pharmacien·nes (le gisement grand public réel) est une **donnée restreinte** "
            f"non couverte ici. Les **{sans_email:,} officines sans e-mail public** sont à "
            f"traiter via la voie B (habilitation DR) ou le lac de données BICOEUR."
        )
    else:
        lines.append(
            "Exécution incluant la **voie B (donnée restreinte)**. Les officines restant "
            "sans e-mail grand public exploitable sont à renvoyer vers le lac BICOEUR."
        )
    lines += [
        "",
        "> RGPD : données à caractère personnel (mission d'intérêt public, art. 6.1.e + 6.3). "
        "Finalité unique = adoption MSSanté. Pas de rediffusion ; stockage non exposé "
        "publiquement (le CSV n'est pas versionné).",
        "",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--probe", action="store_true",
                   help="valide la clé, liste les search params et échantillonne (recommandé au 1er run)")
    p.add_argument("--restreint", action="store_true",
                   help="active la voie B (e-mail de correspondance ; requiert une clé DR)")
    p.add_argument("--bal", metavar="CHEMIN",
                   help="chemin de l'extraction MSSanté (défaut : la plus récente dans . ou ..)")
    p.add_argument("--no-bal", action="store_true",
                   help="désactive l'enrichissement MSSanté (a_bal_mss='inconnu')")
    p.add_argument("--limit", type=int, metavar="N",
                   help="ne traite que les N premières officines (test)")
    p.add_argument("--out", default="out", metavar="DIR",
                   help="dossier de sortie (défaut : ./out)")
    return p


def main():
    args = build_parser().parse_args()
    try:
        client_probe = args.probe
        if client_probe:
            probe(AnnuaireClient(verbose=True))
        else:
            run(args)
    except AnnuaireError as e:
        print(f"\nERREUR : {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\nInterrompu.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
