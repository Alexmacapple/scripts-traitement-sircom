# 29D - Contrat public `reports.py`

Statut : `done`

Dépend de : aucun, peut commencer immédiatement.

À construire : documenter et verrouiller le contrat public de génération des
rapports avant tout nouveau découpage de `sircom2026/reports.py`.

## Énoncé du problème

`reports.py` porte à la fois collecte de données, rendu du rapport métier,
rendu du rapport technique et écriture d'artefacts. Un refactor sans contrat
peut changer le contenu attendu du package final ou réintroduire des valeurs
sensibles dans le rapport technique.

## Solution

Verrouiller les noms d'artefacts, sections du rapport métier, champs techniques
principaux et règles d'absence de données sensibles.

## Critères d'acceptation

- [x] Les artefacts `rapport-metier.md` et `rapport-technique.json` restent
      nommés ainsi.
- [x] Les sections fixes du rapport métier restent listées et testées.
- [x] Le rapport technique conserve les compteurs, durées, tailles, codes
      erreur et traces anonymisées attendues.
- [x] Les scénarios avec images, sans images et avec alertes ouvertes sont
      couverts.
- [x] L'absence de valeurs métier sensibles dans le rapport technique est
      testée.
- [x] Aucun refactor de structure n'est réalisé dans ce ticket.
- [x] `tests.test_reports`, `tests.test_package` et `tests.test_csv_preview`
      passent.

## Hors périmètre

- Changer le format métier des rapports.
- Changer le package final.
- Déplacer les fonctions hors de `reports.py`.

## Garde-fous LLM

- Ne pas embellir les rapports dans ce ticket.
- Ne pas ajouter de nouveaux champs techniques sans besoin de contrat.
- Si un libellé métier est incohérent, le noter séparément au lieu de le
  corriger.

## Preuve attendue

- tests de contrat rapports ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Contrat public à préserver en 33

### Constantes et types publics

Les entrées suivantes de `sircom2026.reports` sont considérées comme publiques
pour le découpage du ticket 33 :

- `REPORTS_STEP_KEY = "rapports"` ;
- `REPORTS_RULES_VERSION = "reports-v1"` ;
- `REPORTS_SCHEMA_VERSION = 1` ;
- `BUSINESS_REPORT_ARTIFACT_KIND = "markdown"` ;
- `BUSINESS_REPORT_ARTIFACT_ROLE = "rapport-metier"` ;
- `BUSINESS_REPORT_FILENAME = "rapport-metier.md"` ;
- `BUSINESS_REPORT_MIME_TYPE = "text/markdown; charset=utf-8"` ;
- `TECHNICAL_REPORT_ARTIFACT_KIND = "json"` ;
- `TECHNICAL_REPORT_ARTIFACT_ROLE = "rapport-technique"` ;
- `TECHNICAL_REPORT_FILENAME = "rapport-technique.json"` ;
- `TECHNICAL_REPORT_MIME_TYPE = "application/json"` ;
- `CurrentJsonArtifact(artifact, payload)` ;
- `PersistedReports(business_artifact, technical_artifact)` ;
- `ReportsNotReady` ;
- `ReportsPrerequisiteMissing(step_key, role)`.

Les fonctions publiques à préserver sont :

- `run_reports_job(context, *, settings)` ;
- `get_persisted_reports(repositories, *, settings, lot_id)` ;
- `build_business_report(snapshot, *, generated_at)` ;
- `build_technical_report(snapshot, *, generated_at)`.

### Artefacts exposés

La route publique des rapports expose uniquement :

- `business_report_artifact` ;
- `technical_report_artifact`.

Chaque artefact public conserve les champs `id`, `kind`, `role`, `status`,
`size_bytes`, `sha256`, `mime_type` et `download_url`, sans chemin local.

### Rapport métier

Le fichier `rapport-metier.md` doit conserver les sections fixes suivantes :

- `Résumé du lot` ;
- `Entrées` ;
- `Décisions utilisateur` ;
- `Diagnostic Excel` ;
- `Mapping` ;
- `Fusion et normalisation` ;
- `CSV` ;
- `Images` ;
- `Intégrité` ;
- `Package` ;
- `Actions attendues`.

Le rapport métier peut afficher des valeurs métier utiles au SIRCOM, dont les
colonnes de mapping, les lignes supprimées, les images présentes ou ignorées et
les alertes ouvertes.

### Rapport technique

Le fichier `rapport-technique.json` conserve les clés de premier niveau :

- `schema_version` ;
- `rules_version` ;
- `generated_at` ;
- `resume_execution` ;
- `sources` ;
- `etapes` ;
- `compteurs` ;
- `codes_erreur` ;
- `traces_anonymisees`.

Le rapport technique conserve :

- le résumé d'exécution `lot_id`, `status` et `open_problem_counts` ;
- les sources amont enregistrées, avec taille, empreinte SHA-256 et type MIME,
  sans `relative_path` ;
- les étapes avec `step_key`, `status`, `run_id`, fingerprints, progression et
  `duration_ms` ;
- les compteurs Excel, fusion, normalisation, CSV et images ;
- les codes d'erreur structurés par `severity`, `code` et `count` ;
- les traces anonymisées avec payloads primitifs et sans chemin local.

Le rapport technique ne doit pas exposer les valeurs métier sensibles utilisées
par les fixtures, ni les noms de fichiers sources qui servent à tester la
bonne anonymisation.

### Scénarios protégés

Les tests verrouillent :

- génération de rapports avec images et alerte image ouverte ;
- génération de rapports sans artefacts images ;
- exposition HTML des liens de téléchargement ;
- présence des rapports dans le package final ;
- compatibilité avec le flux d'aperçu et d'export CSV.

## Livraison

- Aucun refactor de `sircom2026/reports.py` n'a été réalisé.
- `tests/test_reports.py` ajoute un test de contrat des constantes, types et
  signatures des fonctions publiques du module.
- `tests/test_reports.py` renforce la vérification de la réponse API rapports,
  des sections du rapport métier, du schéma du rapport technique et des blocs
  de compteurs.
- Les scénarios existants avec images, sans images et avec alertes ouvertes
  restent les preuves métier du contrat.

Preuves exécutées le 2026-07-23 :

- `uv run --frozen --extra test pytest tests/test_reports.py -q` :
  3 tests passés.
- `uv run --frozen --extra test pytest tests/test_reports.py tests/test_package.py tests/test_csv_preview.py -q` :
  11 tests passés.
- `uv run --frozen --extra test pytest -q` : 232 tests passés, 4 sautés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
- `bash scripts/check-accents.sh projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/29d-contrat-public-reports.md projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/README.md` :
  OK.
