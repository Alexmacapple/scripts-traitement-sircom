# 29C - Contrat public `api/lots.py`

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : verrouiller le contrat public des routes lots avant tout nouveau
découpage de `sircom2026/api/lots.py`.

## Énoncé du problème

`api/lots.py` porte de nombreuses routes publiques. Un refactor de ce fichier
peut conserver une CI verte tout en modifiant un statut HTTP, une forme JSON,
un code d'erreur ou une précondition d'upload.

## Solution

Ajouter une table de contrat des routes lots et renforcer les tests qui
protègent chemins, méthodes, statuts HTTP, codes d'erreur et champs de réponse
principaux.

## Critères d'acceptation

- [ ] Les routes publiques `GET`, `POST` et `DELETE` exposées par
      `/api/lots` sont listées.
- [ ] Les statuts HTTP de succès et d'erreur sont couverts pour les routes
      critiques.
- [ ] Les codes d'erreur métier structurés restent stables.
- [ ] Les préconditions upload Excel, upload images, mapping, tri, CSV,
      rapports et package sont couvertes au moins par tests ciblés.
- [ ] Aucun refactor de structure n'est réalisé dans ce ticket.
- [ ] `tests.test_lots_api`, `tests.test_api_access_errors`,
      `tests.test_image_upload`, `tests.test_package` et
      `tests.test_workflow_failure_paths` passent.

## Hors périmètre

- Déplacer les routes vers plusieurs routers.
- Modifier les contrats JSON.
- Modifier la politique d'accès.

## Garde-fous LLM

- Ce ticket doit rendre le futur refactor mesurable, pas déplacer le code.
- Ne pas créer de snapshots JSON trop larges et fragiles ; tester les champs
  contractuels.
- Ne pas exposer de données personnelles dans les fixtures ou les assertions.

## Preuve attendue

- tests de contrat API lots ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.
