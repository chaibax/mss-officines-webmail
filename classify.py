# -*- coding: utf-8 -*-
"""Normalisation et classification des e-mails.

Logique pure (sans I/O, sans réseau) : facile à tester et à raisonner.
- normalize_email : minuscules, trim, validation regex simple, extraction du domaine.
- classify_domain : grand_public | professionnel | mssante.
"""
import re

import config

# Regex volontairement simple : une seule arobase, un point dans le domaine,
# pas d'espace. On ne cherche pas la conformité RFC exhaustive mais à écarter
# les valeurs manifestement invalides.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw):
    """Retourne (email, domaine) normalisés, ou None si invalide.

    Exemple : "  Contact@Pharma.GMAIL.com " -> ("contact@pharma.gmail.com", ...).
    Note : on ne garde que le dernier segment après « @ » comme domaine.
    """
    if not raw:
        return None
    email = raw.strip().lower()
    # Certains telecom FHIR arrivent préfixés « mailto: ».
    if email.startswith("mailto:"):
        email = email[len("mailto:"):]
    if not _EMAIL_RE.match(email):
        return None
    domain = email.rsplit("@", 1)[1]
    return email, domain


def _is_mssante(domain):
    return domain == "mssante.fr" or any(
        domain.endswith("." + suf) or domain == suf for suf in config.MSSANTE_SUFFIXES
    )


def classify_domain(domain):
    """Classe un domaine : mssante > grand_public > professionnel.

    L'ordre compte : un domaine MSSanté ne doit jamais être compté grand public.
    """
    if _is_mssante(domain):
        return config.CAT_MSSANTE
    if domain in config.GRAND_PUBLIC_DOMAINS:
        return config.CAT_GRAND_PUBLIC
    return config.CAT_PRO
