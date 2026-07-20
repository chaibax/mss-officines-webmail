# -*- coding: utf-8 -*-
"""Enrichissement MSSanté hors API : index des BAL depuis l'extraction locale.

Source : « Annuaire Santé - Extraction des BAL MSSanté » (ANS / data.gouv.fr),
fichier `extraction-correspondance-mssante*.txt` mis à jour quotidiennement,
séparateur « | ». On en tire deux ensembles pour poser le booléen `a_bal_mss`
sans aucun appel API supplémentaire :

  - rpps_with_per_bal   : RPPS (personne) portant au moins une BAL PER publiée
                          -> équipement au niveau du pharmacien (voie B).
  - struct_with_org_bal : identifiants de structure portant une BAL ORG publiée
                          -> l'officine dispose d'une messagerie MSSanté (voie A).

URL stable du fichier :
  https://www.data.gouv.fr/api/1/datasets/r/afe01105-d9a1-41fe-921f-e40ea48b2ba6
"""
import csv
import glob
import os
import sys

# Noms de colonnes utiles dans l'extraction (en-tête « | »).
COL_TYPE = "Type de BAL"                       # ORG | PER | (APP absente du fichier)
COL_RPPS = "Identification nationale PP"       # RPPS de la personne
COL_RPPS_ALT = "Identifiant PP"                # repli si RPPS national vide
COL_STRUCT = "Identification Structure"        # id structure (FINESS/SIRET selon type)


def find_extraction(explicit=None, search_dirs=(".", "..")):
    """Localise le fichier d'extraction : chemin explicite, sinon le plus récent."""
    if explicit:
        if os.path.exists(explicit):
            return explicit
        raise FileNotFoundError(f"Extraction introuvable : {explicit}")
    cands = []
    for d in search_dirs:
        cands += glob.glob(os.path.join(d, "extraction-correspondance-mssante*.txt"))
    if not cands:
        return None
    return max(cands, key=os.path.getmtime)


def _digits(value):
    """Normalise un identifiant en ne gardant que les chiffres (comparaison FINESS)."""
    return "".join(ch for ch in (value or "") if ch.isdigit())


def load_bal_index(path, verbose=True):
    """Retourne (rpps_with_per_bal, struct_with_org_bal, stats).

    Les identifiants de structure sont indexés sous deux formes (brute et
    « chiffres seuls ») pour absorber les écarts de formatage entre l'extraction
    et le FINESS renvoyé par l'API.
    """
    rpps_with_per_bal = set()
    struct_with_org_bal = set()
    n_per = n_org = 0

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            typ = (row.get(COL_TYPE) or "").strip().upper()
            if typ == "PER":
                n_per += 1
                rpps = (row.get(COL_RPPS) or "").strip() or (row.get(COL_RPPS_ALT) or "").strip()
                if rpps:
                    rpps_with_per_bal.add(rpps)
                    rpps_with_per_bal.add(_digits(rpps))
            elif typ == "ORG":
                n_org += 1
                struct = (row.get(COL_STRUCT) or "").strip()
                if struct:
                    struct_with_org_bal.add(struct)
                    struct_with_org_bal.add(_digits(struct))

    stats = {"lignes_per": n_per, "lignes_org": n_org,
             "rpps_distincts": sum(1 for x in rpps_with_per_bal if x.isdigit()),
             "structures_org": sum(1 for x in struct_with_org_bal if x.isdigit())}
    if verbose:
        print(f"  [bal] {n_per:,} BAL PER, {n_org:,} BAL ORG indexées depuis "
              f"{os.path.basename(path)}".replace(",", " "), file=sys.stderr)
    return rpps_with_per_bal, struct_with_org_bal, stats


class BalIndex:
    """Petit wrapper pour poser le booléen a_bal_mss par officine / par RPPS."""

    def __init__(self, rpps_with_per_bal=None, struct_with_org_bal=None):
        self.rpps = rpps_with_per_bal or set()
        self.struct = struct_with_org_bal or set()
        self.available = bool(self.rpps or self.struct)

    @classmethod
    def from_file(cls, path, verbose=True):
        rpps, struct, _ = load_bal_index(path, verbose=verbose)
        return cls(rpps, struct)

    @classmethod
    def empty(cls):
        return cls(set(), set())

    def officine_has_bal(self, finess):
        """L'officine (structure) a-t-elle une BAL ORG MSSanté publiée ?"""
        if not finess:
            return False
        return finess in self.struct or _digits(finess) in self.struct

    def pharmacien_has_bal(self, rpps):
        """Le pharmacien (RPPS) porte-t-il une BAL PER MSSanté publiée ?"""
        if not rpps:
            return False
        return rpps in self.rpps or _digits(rpps) in self.rpps
