# 05 - Preuves adversariales et Ruff check en CI

Statut : `done`

Dépend de : 02, 03, 04.

À construire : la CI prouve que les bornes ressources restent actives et ajoute
le lint Ruff manquant.

## Contexte

La CI exécute déjà `ruff format --check`, la suite pytest avec couverture et le
test navigateur Playwright. La contre-revue GLM signale que `ruff check .` passe
localement mais n'est pas encore exécuté en CI. Les bornes ressources doivent
être verrouillées par tests adversariaux, pas seulement par inspection.

## Critères d'acceptation

- [x] `.github/workflows/ci.yml` ajoute une étape
      `uv run --frozen --extra test ruff check .`.
- [x] Les tests adversariaux Excel construisent un classeur synthétique hors
      limites avec seuils abaissés et vérifient un refus structuré rapide.
- [x] Les tests adversariaux images construisent ou simulent une image hors
      limites avec seuils abaissés et vérifient un refus avant conversion pleine
      résolution.
- [x] Les tests adversariaux couvrent aussi une image bombe Pillow de très petit
      poids disque mais aux dimensions déclarées extrêmes.
- [x] Les tests prouvent qu'un zip déjà invalide par limites globales ne déclenche
      pas d'ouverture Pillow inutile.
- [x] Les tests couvrent l'appel direct de `diagnose_workbook()` sans dépendre du
      préfiltre web d'upload.
- [x] Les tests disque simulent un espace libre insuffisant et vérifient un
      blocage contrôlé d'un job lourd.
- [x] Les cas proches des limites restent acceptés ou couverts dans les tickets
      propriétaires.
- [x] La couverture reste supérieure ou égale au seuil projet.
- [x] Aucun test adversarial ne dépend d'un vrai fichier géant ni d'un temps
      d'exécution long pour prouver le refus.

## Hors périmètre

- Audit de dépendances ou SAST.
- Tests de saturation réelle sur gros fichiers.
- Test InDesign 19.4+ réel.
- Audit lecteur d'écran ou RGAA complet.

## Preuve attendue

- `uv run --frozen --extra test ruff format --check .`
- `uv run --frozen --extra test ruff check .`
- `uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q`
- Si disponible : test navigateur existant avec `SIRCOM_RUN_PLAYWRIGHT=1`.

## Clôture post-ShipGuard

Compléments livrés :

- `027dfad` - image bombs Pillow et ordre des bloqueurs zip ;
- `784632e` - préflight Excel direct.

Preuves finales :

- `uv run --frozen --extra test ruff format --check .` : OK ;
- `uv run --frozen --extra test ruff check .` : OK ;
- `uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q` :
  249 tests passés, 5 ignorés, couverture 89,90 % ;
- `env SIRCOM_RUN_PLAYWRIGHT=1 uv run --frozen --extra test python -m unittest tests.test_lots_playwright` :
  4 tests OK ;
- CI GitHub `30010934717` et `30011364866` vertes.

## Sources locales

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `tests/`
- `docs/audits/2026-07-23-contre-revue-glm.md`
