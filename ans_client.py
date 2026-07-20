# -*- coding: utf-8 -*-
"""Client minimal pour l'API FHIR Annuaire Santé (ANS).

Responsabilités isolées : authentification par en-tête, GET robuste (backoff
exponentiel sur 429 et erreurs serveur, respect de Retry-After), pagination
FHIR via les liens `next` du Bundle. Aucune dépendance externe (urllib stdlib)
pour tourner tel quel sur un poste. La clé n'est jamais journalisée.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import config


class AnnuaireError(RuntimeError):
    """Erreur métier remontée à l'appelant (auth, réseau, HTTP)."""


class AnnuaireClient:
    def __init__(self, api_key=None, base_url=None, verbose=True, timeout=60):
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.api_key = api_key or os.environ.get(config.API_KEY_ENV)
        self.verbose = verbose
        self.timeout = timeout
        if not self.api_key:
            raise AnnuaireError(
                f"Clé API absente. Exporter {config.API_KEY_ENV} avant de lancer "
                f"(clé gratuite « données publiques » sur {config.PORTAIL_URL})."
            )

    # ------------------------------------------------------------- bas niveau
    def _headers(self):
        # La clé part dans l'en-tête Gravitee ; jamais dans l'URL ni les logs.
        return {config.API_KEY_HEADER: self.api_key, "Accept": "application/fhir+json"}

    def _request(self, url, max_retries=6):
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(url, headers=self._headers())
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = self._retry_after(e, attempt)
                    self._log(f"429 (throttling), attente {wait}s "
                              f"[tentative {attempt + 1}/{max_retries + 1}]")
                    time.sleep(wait)
                    continue
                if e.code in (500, 502, 503, 504) and attempt < max_retries:
                    wait = min(60, 2 ** attempt)
                    self._log(f"HTTP {e.code} (serveur), retry dans {wait}s")
                    time.sleep(wait)
                    continue
                body = e.read().decode("utf-8", "replace")[:300] if e.fp else ""
                if e.code in (401, 403):
                    raise AnnuaireError(
                        f"HTTP {e.code} — clé refusée ou périmètre non habilité. "
                        f"L'e-mail de correspondance est une donnée restreinte : "
                        f"une clé « données publiques » ne l'expose pas. Détail : {body}"
                    )
                raise AnnuaireError(f"HTTP {e.code} sur {self._safe(url)} : {body}")
            except urllib.error.URLError as e:
                if attempt < max_retries:
                    wait = min(60, 2 ** attempt)
                    self._log(f"réseau ({e.reason}), retry dans {wait}s")
                    time.sleep(wait)
                    continue
                raise AnnuaireError(f"Réseau injoignable sur {self._safe(url)} : {e}")
        raise AnnuaireError(f"Échec après {max_retries} tentatives : {self._safe(url)}")

    @staticmethod
    def _retry_after(err, attempt):
        ra = err.headers.get("Retry-After")
        if ra and ra.strip().isdigit():
            return min(120, int(ra.strip()))
        return min(120, 2 ** attempt)

    @staticmethod
    def _safe(url):
        # Retire tout éventuel paramètre sensible des messages (défensif).
        return url.split("?")[0] + ("?…" if "?" in url else "")

    def _log(self, msg):
        if self.verbose:
            print(f"  [ans] {msg}", file=sys.stderr)

    # -------------------------------------------------------------- haut niveau
    def metadata(self):
        """CapabilityStatement — paramètres réellement disponibles pour la clé."""
        return self._request(f"{self.base_url}/metadata?_format=json")

    def search_pages(self, resource, params):
        """Générateur de Bundles : suit les liens `next` jusqu'à épuisement."""
        query = urllib.parse.urlencode(params, doseq=True, safe="|,$")
        url = f"{self.base_url}/{resource}?{query}"
        while url:
            bundle = self._request(url)
            yield bundle
            url = self._next_link(bundle)

    def search_resources(self, resource, params):
        """Générateur de ressources (aplati les entrées de chaque Bundle)."""
        for bundle in self.search_pages(resource, params):
            for entry in bundle.get("entry", []) or []:
                res = entry.get("resource")
                if res:
                    yield res

    def _next_link(self, bundle):
        for link in bundle.get("link", []) or []:
            if link.get("relation") == "next" and link.get("url"):
                return self._rebase(link["url"])
        return None

    def _rebase(self, url):
        """Réécrit le host du lien `next` sur la passerelle configurée.

        Certaines passerelles renvoient un lien `next` pointant vers un host
        interne : on conserve le chemin/la query mais on force scheme+host de
        BASE_URL pour que la clé et la route restent valides.
        """
        base = urllib.parse.urlsplit(self.base_url)
        nxt = urllib.parse.urlsplit(url)
        if nxt.netloc and nxt.netloc != base.netloc:
            nxt = nxt._replace(scheme=base.scheme, netloc=base.netloc)
        return urllib.parse.urlunsplit(nxt)
