# 33 - Découper `reports.py` sans changer les rapports générés

Statut : `done`

Dépend de : 29D.

À construire : réduire la taille et la responsabilité de
`sircom2026/reports.py` après verrouillage du contrat public, sans changer les
rapports générés ni les artefacts associés.

## Énoncé du problème

`reports.py` mélange collecte des données, rendu du rapport métier, rendu du
rapport technique et écriture transactionnelle des artefacts. Un refactor trop
large peut modifier le contenu final ou réintroduire des données sensibles.

## Solution

Extraire une responsabilité cohérente, par exemple le rendu métier ou le rendu
technique, en gardant l'orchestration de job et les écritures transactionnelles
stables.

## Critères d'acceptation

- [x] Le contrat du ticket 29D est présent et vert avant déplacement.
- [x] Les noms d'artefacts ne changent pas.
- [x] Les sections du rapport métier ne changent pas.
- [x] Le schéma principal du rapport technique ne change pas.
- [x] Les garanties d'absence de données sensibles restent testées.
- [x] Les tests rapports, package et CSV preview restent verts.
- [x] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
      `reports.py`.

## Hors périmètre

- Améliorer le contenu éditorial des rapports.
- Changer le format JSON technique.
- Modifier le package final.
- Refactoriser d'autres modules lourds.

## Garde-fous LLM

- Ne pas mélanger rendu et écriture d'artefacts dans la même extraction.
- Ne pas supprimer de section au motif qu'elle paraît redondante.
- Ne pas exposer de valeurs métier sensibles dans de nouveaux tests ou logs.

## Preuve attendue

- tests du ticket 29D ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Livraison

Découpage réalisé :

- `sircom2026/reports_rendering.py` contient maintenant le rendu du rapport
  métier Markdown, le rendu du rapport technique JSON et les helpers de rendu
  associés : tableaux de mapping, lignes d'onglets, alertes CSV, lignes
  d'actions, entrées techniques de sources, étapes, codes d'erreur, traces
  anonymisées et conversions de valeurs.
- `sircom2026/reports.py` conserve les constantes et types publics du contrat
  29D, les signatures publiques `build_business_report` et
  `build_technical_report` sous forme de wrappers, la collecte du snapshot, les
  préconditions, les écritures transactionnelles d'artefacts et la gestion de
  bail worker.
- Les constantes publiques `REPORTS_SCHEMA_VERSION`,
  `REPORTS_RULES_VERSION` et `TECHNICAL_EVENT_PAYLOAD_KEYS` restent portées par
  `reports.py` et sont injectées dans le renderer technique.
- Le helper privé mort `_problem_counts` a été supprimé, sans changement de
  comportement observable.

Résultat structurel :

- `sircom2026/reports.py` passe de 1071 à 659 lignes.
- `sircom2026/reports_rendering.py` contient 458 lignes dédiées au rendu.

Preuves exécutées le 2026-07-23 :

- Avant déplacement,
  `uv run --frozen --extra test pytest tests/test_reports.py tests/test_package.py tests/test_csv_preview.py -q` :
  11 tests passés.
- Après déplacement, `uv run --frozen --extra test pytest tests/test_reports.py -q` :
  3 tests passés.
- Après déplacement,
  `uv run --frozen --extra test pytest tests/test_reports.py tests/test_package.py tests/test_csv_preview.py -q` :
  11 tests passés.
- `uv run --frozen --extra test pytest -q` : 232 tests passés, 4 sautés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
- `bash scripts/check-accents.sh projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/33-decouper-reports-sans-changer-rapports.md projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/README.md` :
  OK.
