# 32 - Découper `api/lots.py` sans changer les routes publiques

Statut : `done`

Dépend de : 29C.

À construire : réduire la taille de `sircom2026/api/lots.py` après verrouillage
du contrat public, sans changer les routes, statuts HTTP, codes d'erreur ou
formes JSON.

## Énoncé du problème

`api/lots.py` agrège beaucoup d'endpoints et de helpers de réponse. Un refactor
peut facilement déplacer une précondition, oublier une traduction d'erreur ou
modifier un champ JSON attendu par l'interface.

## Solution

Extraire une responsabilité périphérique et testée, par exemple les builders de
réponses ou les traducteurs d'erreurs, en gardant les routes publiques dans un
état lisible et compatible.

## Critères d'acceptation

- [x] Le contrat du ticket 29C est présent et vert avant déplacement.
- [x] Les chemins publics `/api/lots...` ne changent pas.
- [x] Les statuts HTTP, codes d'erreur et champs JSON contractuels ne changent
      pas.
- [x] Les helpers extraits restent internes au package API.
- [x] Les tests API lots, accès, uploads, package et erreurs workflow restent
      verts.
- [x] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
      `api/lots.py`.

## Hors périmètre

- Changer la politique d'accès.
- Créer une nouvelle version d'API.
- Modifier les workflows métier.
- Refactoriser les modules de domaine appelés par l'API.

## Garde-fous LLM

- Ne pas déplacer toutes les routes en une seule passe.
- Ne pas modifier les signatures de route.
- Ne pas élargir ou réduire les informations exposées par les réponses.

## Preuve attendue

- tests du ticket 29C ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Livraison

Découpage réalisé :

- `sircom2026/api/lots_contract.py` contient maintenant les adaptateurs internes
  du contrat API lots : codes d'erreur de validation mapping persistée, erreurs
  transverses `lot_not_found` et `lot_not_mutable`, précondition de mutabilité
  avant upload, conversion des soumissions mapping, sérialisation publique des
  artefacts, traduction des erreurs métier en `ApiError` et lecture de la clé
  d'idempotence.
- `sircom2026/api/lots.py` conserve toutes les routes publiques, les modèles de
  requête Pydantic, les statuts HTTP de route, l'orchestration des endpoints et
  les appels aux modules métier.
- Aucun chemin `/api/lots...`, statut HTTP, code d'erreur structuré ou champ JSON
  contractuel n'a été modifié.
- Les helpers extraits restent dans le package interne `sircom2026.api`.

Résultat structurel :

- `sircom2026/api/lots.py` passe de 1114 à 1007 lignes.
- `sircom2026/api/lots_contract.py` contient les adaptateurs de contrat
  périphériques.

Contrôle Loriq :

- Baseline audit-only exécutée avant refactor :
  `/private/tmp/madeinfrance-loriq-ticket32-baseline.json`.
- Résultat Loriq : `finding_count=0`, `status=incomplete`,
  `unknown_count=21`, `task_queue=[]`.
- Limite Loriq observée : la commande a quitté avec le code `3` et
  `audited_project_changed=true`, mais `git status --porcelain` du dépôt audité
  est resté vide juste après l'exécution. Le rapport est conservé comme repère,
  pas comme preuve bloquante.
- Contexte durable : aucun paquet `why-context` spécifique à ce refactor n'a été
  trouvé avant livraison ; la source de vérité utilisée reste le ticket 32 et le
  contrat public 29C.

Preuves exécutées le 2026-07-23 :

- Avant déplacement,
  `uv run --frozen --extra test pytest tests/test_lots_api.py tests/test_api_access_errors.py tests/test_image_upload.py tests/test_excel_upload.py tests/test_package.py tests/test_workflow_failure_paths.py -q` :
  64 tests passés.
- Après déplacement,
  `uv run --frozen --extra test pytest tests/test_lots_api.py tests/test_api_access_errors.py tests/test_image_upload.py tests/test_excel_upload.py tests/test_package.py tests/test_workflow_failure_paths.py -q` :
  64 tests passés.
- `uv run --frozen --extra test pytest -q` : 232 tests passés, 4 sautés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
- `bash scripts/check-accents.sh projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/32-decouper-api-lots-sans-changer-routes.md projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/README.md` :
  OK.
- `git status --short --branch` : changements limités aux deux documents du
  ticket 32, à `sircom2026/api/lots.py` et à `sircom2026/api/lots_contract.py`
  avant commit.
