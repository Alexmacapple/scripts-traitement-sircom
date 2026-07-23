# Sircom Made in France - traitement 2026

Ce dépôt porte le chantier Sircom 2026 pour produire des livrables compatibles
InDesign à partir d'un Excel multi-onglets et d'un lot d'images.

## Parcours disponibles

- Parcours principal candidat : application web locale `sircom2026/`, avec
  FastAPI, SQLite, worker, interface DSFR, validation Excel, mapping, CSV,
  images, rapport et package final.
- Alternative scriptée : `re-run-old-script-2026/`, copie isolée des anciens
  scripts adaptée au jeu de test 2026.
- Référence historique : `scripts-2025/`. Ne pas modifier cette chaîne pour les
  besoins 2026.

## Sources utiles

- `AGENTS.md` : règles projet et preuves minimales attendues.
- `TODO.md` : état opérationnel et restes à faire.
- `CHANGELOG.md` : historique synthétique.
- `docs/specs/` : contrats fonctionnels, données, orchestration et
  architecture 2026.
- `docs/tickets/` : tickets et preuves des incréments 2026.
- `re-run-old-script-2026/README.md` : mode d'emploi de la voie scriptée.
- `re-run-old-script-2026/docs/` : documentation progressive de la voie
  scriptée.
- `.github/workflows/ci.yml` : CI GitHub Actions versionnée.

Les données réelles et livrables locaux sont sous `livrables-miweb/`, ignorés
par Git.

## Jeu de test officiel

```text
livrables-miweb/livrables-2026/jeux-test-23-juillet/excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx
livrables-miweb/livrables-2026/jeux-test-23-juillet/images-jeux-test-2026.zip
```

Règles d'entrée :

- utiliser les onglets `BDD TT + ANALYSE DGDDI` et `Etablissements` ;
- ignorer les lignes cachées ;
- faire la correspondance sur `Dossier ID` ;
- utiliser le tri région puis département du site de production quand il est
  validé.

## Règles métier 2026

- `imageid` vaut `{id_dossier_normalise}.jpg`, sans préfixe `dossier-`.
- `@pathimg` est renseigné depuis `imageid`.
- Racine `@pathimg` par défaut :
  `Macintosh HD:Users:victoria:Documents:export-jpg-resize`.
- La racine `@pathimg` est configurable par l'UI, l'API et la voie scriptée.
- Les cellules métier vides dans les lignes exportées sortent en `#N/A`.
- Les lignes sans `Dossier ID` sont supprimées.
- Les colonnes entièrement vides sont supprimées.
- Les images absentes sont des alertes non bloquantes.
- Les images finales sont des JPG redimensionnés, destinés au dossier
  `export-jpg-resize/`.

## Application web 2026

Installation locale :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[test]"
.venv/bin/python -m playwright install chromium
```

Lancement :

```bash
.venv/bin/python -m uvicorn sircom2026.app:app --host 127.0.0.1 --port 8000
```

URL locale :

```text
http://127.0.0.1:8000
```

Routes utiles :

- `GET /health`
- `GET /health/ready`
- `GET /api/config/limits`
- `POST /api/lots`
- `GET /api/lots`
- `GET /api/lots/{lot_id}`
- `POST /api/lots/{lot_id}/excel`
- `GET /api/lots/{lot_id}/excel/diagnostic`
- `POST /api/lots/{lot_id}/retry`
- `DELETE /api/lots/{lot_id}`
- `GET /api/lots/{lot_id}/downloads/{artifact_id}`
- `/docs`
- `/openapi.json`

Worker local ponctuel :

```bash
.venv/bin/python scripts-2026/run_worker_once.py --once
```

## Alternative scriptée 2026

Le fichier unique à modifier pour changer de lot est :

```text
re-run-old-script-2026/variables.md
```

Run complet :

```bash
.venv/bin/python re-run-old-script-2026/run_jeu_test_2026.py --clean
```

Sorties par défaut :

```text
re-run-old-script-2026/livrables_output_YYYY-MM-DD/
```

Sorties principales :

- `10-final-sircom-indesign-utf16.csv` : CSV final UTF-16 pour InDesign.
- `11-export-images-id-dossier-rename-resize/` : images JPG traitées.
- `12-mapping-colonnes-sircom-2026.xlsx` et `.csv` : mapping.
- `run-2026-summary.json` : résumé du run.

Dernier run contrôlé : `re-run-old-script-2026/livrables_output_2026-07-24/`.

Résultat contrôlé :

- 561 lignes CSV ;
- 20 colonnes ;
- 392 cellules `#N/A` ;
- 0 cellule vide dans les lignes exportées ;
- 0 inversion de tri région/département ;
- 10 images JPG traitées.

## Vérifications

Tests Python ciblés :

```bash
.venv/bin/python -m unittest tests.test_excel_diagnostic
.venv/bin/python -m unittest tests.test_web_socle tests.test_api_access_errors \
  tests.test_database tests.test_lots_api tests.test_artifacts tests.test_state \
  tests.test_worker tests.test_invalidation tests.test_excel_upload \
  tests.test_excel_diagnostic_pipeline
```

Test navigateur opt-in :

```bash
SIRCOM_RUN_PLAYWRIGHT=1 .venv/bin/python -m unittest tests.test_lots_playwright
```

Contrôles CI versionnés :

- `ruff format --check .`
- `ruff check .`
- `pytest --cov=sircom2026`
- test navigateur Playwright opt-in

## Données et Git

Ne pas commiter les données réelles, exports générés, logs, sauvegardes, zips
images ou images optimisées sauf demande explicite.

Ignorés par Git :

- `livrables-miweb/` ;
- `re-run-old-script-2026/livrables_output_*/` ;
- `.hermes/` ;
- `.claude/` ;
- `.agents/skills/`.

Versionné :

- `.github/workflows/ci.yml`.

## Version

Version : 5.0

Dernière mise à jour : 24 juillet 2026
