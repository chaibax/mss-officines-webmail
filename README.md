# Officines à e-mail « grand public » — cibles d'adoption MSSanté

Constitue une liste ciblée d'**officines** (pharmacies de ville) dont l'adresse
e-mail de contact relève d'un **webmail grand public** (`gmail.com` et
équivalents), via l'**API FHIR Annuaire Santé** de l'ANS — sans aucun scraping.

**Hypothèse de travail :** une adresse de contact en webmail grand public est un
marqueur de faible maturité numérique et de non-équipement MSSanté, donc une
**cible de conversion prioritaire**.

> ⚠️ **RGPD — lisez ceci d'abord.** Les e-mails de correspondance sont des
> **données à caractère personnel**. Traitement fondé sur une mission d'intérêt
> public (art. 6.1.e + 6.3 RGPD), **finalité unique = adoption de MSSanté**. Ce
> dépôt ne contient **que du code**. Les sorties (`out/`, `*.csv`, `synthese.md`)
> et l'extraction MSSanté sont **exclues du versionnement** (`.gitignore`) et ne
> doivent jamais être publiées.

---

## 1. Obtenir une clé API (l'étape qui débloque tout)

L'API renvoie **HTTP 403 sans clé**, y compris sur `/metadata`. Deux niveaux :

| Niveau | Ce qu'on obtient | Comment |
|---|---|---|
| **Données publiques** (self-service) | Énumération des officines + e-mails déclarés au **niveau structure** (voie A). | Créer un compte sur **[portail.openfhir.annuaire.sante.fr](https://portail.openfhir.annuaire.sante.fr/)** → s'abonner à l'API « Annuaire Santé FHIR » → récupérer la clé. Gratuit. |
| **Données restreintes** (habilitation) | E-mail de **correspondance des pharmacien·nes** — le vrai gisement grand public (voie B). | **Formulaire de demande d'accès aux données restreintes** auprès de l'ANS (justifier la finalité). |

**Pourquoi ça compte :** l'e-mail personnel de correspondance (type gmail) est une
**donnée restreinte**. Le niveau public expose surtout l'adresse/téléphone de la
structure et la **BAL MSSanté** (`@mssante.fr`) — qui, par définition, n'est jamais
« grand public ». Sans habilitation DR, la voie A capte seulement les e-mails que
l'officine a déclarés au niveau structure (volume limité) ; le reste est renvoyé
vers la voie B ou le lac de données **BICOEUR**.

```bash
export ANS_API_KEY="votre_cle"      # ne jamais coder en dur / committer
```

## 2. Lancer

Aucune dépendance à installer (bibliothèque standard Python 3.9+).

```bash
# 1er run recommandé : valide la clé, liste les search params, échantillonne 1 officine
python3 extract_officines.py --probe

# Extraction voie A (données publiques) + enrichissement + CSV/synthèse
python3 extract_officines.py

# + voie B (e-mail de correspondance ; requiert une clé données restreintes)
python3 extract_officines.py --restreint

# Test rapide sur 200 officines
python3 extract_officines.py --limit 200
```

Équivalents `make` : `make probe`, `make run`, `make restreint`, `make test`.

## 3. Enrichissement MSSanté (hors API)

Le booléen `a_bal_mss` est calculé **sans appel API**, en croisant avec
l'extraction quotidienne « Annuaire Santé - Extraction des BAL MSSanté »
([data.gouv.fr](https://www.data.gouv.fr/api/1/datasets/r/afe01105-d9a1-41fe-921f-e40ea48b2ba6)) :

- **niveau officine** — la structure (FINESS) porte-t-elle une **BAL ORG** publiée ?
- **niveau pharmacien** — le **RPPS** porte-t-il une **BAL PER** publiée ? (voie B)

Placez le fichier `extraction-correspondance-mssante*.txt` dans le dossier courant
ou son parent (détection auto du plus récent), ou passez `--bal CHEMIN`. Sans
extraction, `a_bal_mss = "inconnu"`.

## 4. Sorties (`out/`)

- **`officines_email_grand_public.csv`** (séparateur `;`, UTF-8) — colonnes :
  `finess;raison_sociale;adresse;code_postal;ville;rpps;nom;prenom;email;domaine;categorie_domaine;a_bal_mss;source`
  avec `source ∈ {organization_public, practitioner_restreint}`. La colonne
  `a_bal_mss` distingue les **deux cibles** : `non` = à équiper (sans MSSanté),
  `oui` = à accompagner (déjà équipée, joignable sur sa boîte grand public).
- **`officines_email_professionnel.csv`** — mêmes colonnes, pour les e-mails à
  **domaine propre** (« non public » : ni webmail, ni MSSanté). Contactables hors
  espace de confiance MSSanté.
- **`synthese.md`** — parc, couverture e-mail, répartition par catégorie, top
  domaines (grand public **et** professionnels), les deux cibles, écart d'habilitation.
- **`agregats.json`** — dénombrements uniquement (aucune donnée nominative), source
  du dashboard.

Les CSV contiennent des données personnelles → **jamais versionnés** (`.gitignore`).

## 5. Architecture

| Fichier | Rôle |
|---|---|
| `config.py` | Endpoints, en-tête d'auth, nomenclatures, **liste des domaines grand public** (seul fichier à éditer pour l'étendre). |
| `classify.py` | Normalisation e-mail + classification `grand_public` / `professionnel` / `mssante` (logique pure, testée). |
| `ans_client.py` | Client FHIR : auth par en-tête, backoff 429, pagination `next`. Aucune dépendance. |
| `bal_index.py` | Index des BAL MSSanté depuis l'extraction locale (enrichissement `a_bal_mss`). |
| `extract_officines.py` | Orchestration : voie A → voie B → enrichissement → CSV + synthèse. CLI. |
| `test_classify.py` | Tests unitaires (offline). |

## 6. Robustesse & conformité

- Clé en **variable d'environnement**, jamais journalisée ni mise en URL.
- **Backoff exponentiel** sur HTTP 429 (respect de `Retry-After`) et erreurs serveur.
- **Pagination** via `Bundle.link[next]` jusqu'à épuisement (~21 000 officines).
- `telecom` absent ⇒ ligne comptée « sans e-mail », pas d'échec du script.
- Réécriture propre du CSV (idempotent) ; dédoublonnage par `(finess, e-mail)`.
- Codes/nomenclatures (`type=620`, profession `21`, systèmes) confirmés au 1er run
  via `--probe` (CapabilityStatement `/metadata`).

## Références

- Modèle & profils FHIR (DP/DR) : https://interop.esante.gouv.fr/ig/fhir/annuaire
- Documentation API : https://ansforge.github.io/annuaire-sante-fhir-documentation/
- CapabilityStatement : https://gateway.api.esante.gouv.fr/fhir/v2/metadata
- Portail d'accès (clé) : https://portail.openfhir.annuaire.sante.fr/
