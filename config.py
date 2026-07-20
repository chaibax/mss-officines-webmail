# -*- coding: utf-8 -*-
"""Configuration — endpoints, en-tête d'authentification, nomenclatures, domaines webmail.

Tout est surchargeable par variable d'environnement pour ne rien coder en dur
(clé API notamment). La liste des domaines « grand public » est maintenue ici :
c'est le seul fichier à éditer pour l'étendre.
"""
import os

# --------------------------------------------------------------------- API ANS
# API FHIR Annuaire Santé (ANS), norme FHIR R4. Base confirmée sur le dépôt
# officiel ansforge/annuaire-sante-fhir-documentation (README).
BASE_URL = os.environ.get(
    "ANS_BASE_URL", "https://gateway.api.esante.gouv.fr/fhir/v2"
).rstrip("/")

# La clé n'est JAMAIS codée en dur : elle vient de la variable d'environnement.
API_KEY_ENV = "ANS_API_KEY"

# En-tête portant la clé. Confirmé en direct sur la passerelle : « ESANTE-API-KEY »
# (le paramètre de requête ?api-key= fonctionne aussi). Surchargeable si besoin.
API_KEY_HEADER = os.environ.get("ANS_API_KEY_HEADER", "ESANTE-API-KEY")

# Portail d'obtention de la clé (données publiques, self-service).
PORTAIL_URL = "https://portail.openfhir.annuaire.sante.fr/"

# Taille de page : on demande le maximum autorisé, la pagination suit les liens next.
PAGE_SIZE = int(os.environ.get("ANS_PAGE_SIZE", "1000"))

# ------------------------------------------------------------- Nomenclatures
# Catégorie d'établissement FINESS 620 = « Pharmacie d'officine » (exclut la PUI).
# À confirmer au 1er run via `--probe` (CapabilityStatement + échantillon).
OFFICINE_TYPE_CODE = os.environ.get("ANS_OFFICINE_TYPE", "620")

# Système de la catégorie d'établissement (fallback si le jeton nu est refusé :
# la requête devient alors type={system}|620). Valeur MOS/NOS de l'ANS.
OFFICINE_TYPE_SYSTEM = os.environ.get(
    "ANS_OFFICINE_TYPE_SYSTEM",
    "https://mos.esante.gouv.fr/NOS/TRE_R66-CategorieEtablissement/FHIR/"
    "TRE-R66-CategorieEtablissement",
)

# Code profession pharmacien (nomenclature TRE_G15-ProfessionSante). Cf. étage 1 :
# 21 = Pharmacien (10 = Médecin, 40 = Chirurgien-Dentiste, 50 = Sage-Femme).
PHARMACIEN_CODE = os.environ.get("ANS_PHARMACIEN_CODE", "21")

# ----------------------------------------------------------------- Domaines
# Webmail / FAI grand public. Marqueur de faible maturité numérique => cible.
GRAND_PUBLIC_DOMAINS = {
    # Google
    "gmail.com", "googlemail.com",
    # Microsoft
    "hotmail.com", "hotmail.fr", "outlook.com", "outlook.fr", "live.fr", "msn.com",
    # Yahoo
    "yahoo.com", "yahoo.fr", "ymail.com",
    # Orange
    "orange.fr", "wanadoo.fr",
    # Free
    "free.fr",
    # SFR
    "sfr.fr", "neuf.fr",
    # Bouygues
    "bbox.fr",
    # La Poste
    "laposte.net",
    # Apple / autres
    "icloud.com", "me.com", "aol.com", "gmx.fr", "gmx.com", "proton.me", "protonmail.com",
}

# Suffixes de confiance MSSanté : jamais « grand public », exclus de la sortie.
# Couvre mssante.fr et tous les sous-domaines opérateurs (ex. aura.mssante.fr).
MSSANTE_SUFFIXES = ("mssante.fr",)

# Catégories de domaine possibles.
CAT_GRAND_PUBLIC = "grand_public"
CAT_PRO = "professionnel"
CAT_MSSANTE = "mssante"
