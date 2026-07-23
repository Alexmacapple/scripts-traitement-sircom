# 27 - Corriger le packaging des partials Jinja

Statut : `done`

Dépend de : aucun, peut commencer immédiatement.

À construire : garantir que les templates Jinja inclus dans
`sircom2026/templates/partials/` sont embarqués dans le package Python installé,
pas seulement disponibles dans le dépôt source.

## Énoncé du problème

Le découpage Jinja a déplacé une partie de l'interface dans
`sircom2026/templates/partials/`. La configuration de package doit couvrir ces
partials explicitement, sinon une installation depuis une archive ou une wheel
peut démarrer sans certains fragments de template.

## Solution

Mettre à jour la configuration de package pour inclure les templates racine et
les partials. Ajouter une preuve automatisée ou un test de packaging qui échoue
si un partial attendu n'est pas disponible après installation ou via les
ressources du package.

## Critères d'acceptation

- [x] Les fichiers `sircom2026/templates/*.html` restent inclus.
- [x] Les fichiers `sircom2026/templates/partials/*.html` sont inclus.
- [x] Un test ou une commande de packaging vérifie au moins un partial réel,
      par exemple `partials/header.html` et `partials/workflow_view.html`.
- [x] L'application installée peut rendre `/` sans `TemplateNotFound`.
- [x] `uv run --frozen --extra test pytest -q` passe.

## Hors périmètre

- Redécouper les templates.
- Modifier le design DSFR, les libellés visibles ou les identifiants HTML.
- Déplacer les assets DSFR.

## Garde-fous LLM

- Ne pas régler ce risque par un chemin absolu vers le dépôt.
- Ne pas ajouter les fichiers générés ou les artefacts locaux au package.
- La preuve doit porter sur le package ou les ressources Python, pas seulement
  sur la présence des fichiers dans le workspace.

## Preuve attendue

- test de packaging ou smoke test d'installation ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Livraison

- `pyproject.toml` inclut maintenant `templates/partials/*.html` dans les
  données embarquées du package `sircom2026`.
- `tests/test_package_data.py` vérifie la déclaration de packaging et l'accès
  aux ressources `partials/header.html` et `partials/workflow_view.html`.
- Preuves exécutées le 2026-07-23 :
  - `uv run --frozen --extra test python -m unittest tests.test_package_data` :
    2 tests OK ;
  - `uv run --frozen --extra test pytest -q` : 223 tests passés, 4 ignorés ;
  - `uv run --frozen --extra test ruff check .` : OK ;
  - `git diff --check` : OK.
