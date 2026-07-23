# -*- coding: utf-8 -*-
"""Logos simplifiés (SVG inline) des fournisseurs d'e-mail grand public + libellés.

Marques stylisées et reconnaissables (couleur + monogramme), sans dépendance
externe (CSP-safe). Ce ne sont pas les logos officiels au pixel près.
"""

# domaine -> (libellé lisible, couleur de fond, couleur texte, monogramme)
_BRANDS = {
    "gmail.com": ("Gmail", "#ffffff", "#ea4335", "M"),
    "googlemail.com": ("Gmail", "#ffffff", "#ea4335", "M"),
    "orange.fr": ("Orange", "#ff7900", "#000000", "or"),
    "wanadoo.fr": ("Wanadoo · Orange", "#ff7900", "#ffffff", "w"),
    "hotmail.fr": ("Hotmail", "#0072c6", "#ffffff", "H"),
    "hotmail.com": ("Hotmail", "#0072c6", "#ffffff", "H"),
    "outlook.fr": ("Outlook", "#0f6cbd", "#ffffff", "O"),
    "outlook.com": ("Outlook", "#0f6cbd", "#ffffff", "O"),
    "live.fr": ("Live · Microsoft", "#0f6cbd", "#ffffff", "L"),
    "msn.com": ("MSN", "#0f6cbd", "#ffffff", "m"),
    "yahoo.fr": ("Yahoo", "#5f01d1", "#ffffff", "Y!"),
    "yahoo.com": ("Yahoo", "#5f01d1", "#ffffff", "Y!"),
    "ymail.com": ("Yahoo · ymail", "#5f01d1", "#ffffff", "y"),
    "free.fr": ("Free", "#cd1e25", "#ffffff", "f"),
    "sfr.fr": ("SFR", "#e0001b", "#ffffff", "sfr"),
    "neuf.fr": ("Neuf · SFR", "#e0001b", "#ffffff", "n"),
    "bbox.fr": ("Bbox · Bouygues", "#009bce", "#ffffff", "b"),
    "laposte.net": ("La Poste", "#ffcd00", "#003b7a", "LP"),
    "icloud.com": ("iCloud", "#ffffff", "#3693f3", "i"),
    "me.com": ("iCloud · me", "#ffffff", "#3693f3", "i"),
    "aol.com": ("AOL", "#1176e7", "#ffffff", "Ao"),
    "gmx.fr": ("GMX", "#1c449b", "#ffffff", "g"),
    "gmx.com": ("GMX", "#1c449b", "#ffffff", "g"),
    "proton.me": ("Proton Mail", "#6d4aff", "#ffffff", "P"),
    "protonmail.com": ("Proton Mail", "#6d4aff", "#ffffff", "P"),
}


def label(domain):
    return _BRANDS.get(domain, (domain, None, None, None))[0]


def logo_svg(domain, size=26):
    """Chip SVG (coin arrondi, couleur de marque, monogramme)."""
    b = _BRANDS.get(domain)
    if not b:
        # fallback : chip gris avec l'initiale
        _, bg, fg, mono = domain, "#e5e5e5", "#3a3a3a", (domain[:1] or "?").upper()
    else:
        _, bg, fg, mono = b
    stroke = ' stroke="#e5e5e5" stroke-width="1"' if bg.lower() == "#ffffff" else ""
    fs = 12 if len(mono) <= 1 else (9.5 if len(mono) == 2 else 8)
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'role="img" aria-label="{label(domain)}" xmlns="http://www.w3.org/2000/svg" '
        f'style="flex:0 0 auto;display:block">'
        f'<rect x="0.5" y="0.5" width="{size-1}" height="{size-1}" rx="6" fill="{bg}"{stroke}/>'
        f'<text x="{size/2}" y="{size/2}" fill="{fg}" font-size="{fs}" font-weight="700" '
        f'font-family="Marianne,Arial,sans-serif" text-anchor="middle" '
        f'dominant-baseline="central">{mono}</text></svg>'
    )
