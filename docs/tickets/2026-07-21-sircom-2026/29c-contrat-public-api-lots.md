# 29C - Contrat public `api/lots.py`

Statut : `done`

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

- [x] Les routes publiques `GET`, `POST` et `DELETE` exposées par
      `/api/lots` sont listées.
- [x] Les statuts HTTP de succès et d'erreur sont couverts pour les routes
      critiques.
- [x] Les codes d'erreur métier structurés restent stables.
- [x] Les préconditions upload Excel, upload images, mapping, tri, CSV,
      rapports et package sont couvertes au moins par tests ciblés.
- [x] Aucun refactor de structure n'est réalisé dans ce ticket.
- [x] `tests.test_lots_api`, `tests.test_api_access_errors`,
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

## Contrat public à préserver en 32

### Routes du router `sircom2026.api.lots`

| Méthode | Route | Succès nominal |
|---|---|---|
| `GET` | `/api/lots` | `200` |
| `POST` | `/api/lots` | `201` |
| `GET` | `/api/lots/{lot_id}` | `200` |
| `DELETE` | `/api/lots/{lot_id}` | `200` ou `202` si purge différée |
| `POST` | `/api/lots/{lot_id}/retry` | `202` |
| `POST` | `/api/lots/{lot_id}/excel` | `202` |
| `GET` | `/api/lots/{lot_id}/excel/diagnostic` | `200` |
| `POST` | `/api/lots/{lot_id}/images` | `202` |
| `GET` | `/api/lots/{lot_id}/images/status` | `200` |
| `GET` | `/api/lots/{lot_id}/images/matching` | `200` |
| `POST` | `/api/lots/{lot_id}/images/resolutions` | `202` |
| `GET` | `/api/lots/{lot_id}/mapping` | `200` |
| `POST` | `/api/lots/{lot_id}/mapping/draft` | `200` |
| `POST` | `/api/lots/{lot_id}/mapping/validate` | `200` |
| `POST` | `/api/lots/{lot_id}/mapping/profile` | `201` |
| `POST` | `/api/lots/{lot_id}/mapping/profile-draft` | `200` |
| `GET` | `/api/lots/{lot_id}/tri` | `200` |
| `POST` | `/api/lots/{lot_id}/tri/validate` | `200` |
| `GET` | `/api/lots/{lot_id}/csv/preview` | `200` |
| `POST` | `/api/lots/{lot_id}/csv/preview/validate` | `200` |
| `GET` | `/api/lots/{lot_id}/csv/export` | `200` |
| `GET` | `/api/lots/{lot_id}/reports` | `200` |
| `POST` | `/api/lots/{lot_id}/package` | `202` |
| `GET` | `/api/lots/{lot_id}/package` | `200` |

La route `/api/lots/{lot_id}/downloads/{artifact_id}` est exposée sous le
même préfixe public, mais elle appartient au module downloads et reste hors
contrat de découpage de `api/lots.py`.

### Réponses publiques

Les réponses de succès doivent conserver les champs principaux suivants :

- création, lecture et liste : `lot`, `items`, `pagination` selon la route ;
- upload Excel et images : `lot`, `artifact`, `job`,
  `invalidated_steps` ;
- diagnostic Excel et inspection images : payload métier, `problems`,
  `problem_groups`, `artifact` ;
- mapping : `mapping`, `profiles`, `artifact`, `lot`,
  `invalidated_steps` selon l'action ;
- tri : `proposal`, `decision`, `artifact`, `lot`, `invalidated_steps` ;
- CSV : `preview`, `preview_artifact`, `csv_artifact`, `artifact`, `lot`,
  `invalidated_steps` selon la route ;
- rapports : `business_report_artifact`, `technical_report_artifact` ;
- package : `lot`, `job` ou `artifact` ;
- suppression : `lot`, `cancel_requested_jobs`, `purge`.

Tous les artefacts publics passent par une forme sans chemin interne :
`id`, `kind`, `role`, `status`, `size_bytes`, `sha256`, `mime_type`,
`download_url`.

### Codes d'erreur structurés figés

Codes transverses :

- `SIRCOM_LOT_NOT_FOUND`.
- `SIRCOM_LOT_NOT_MUTABLE`.
- `SIRCOM_IDEMPOTENCY_KEY_INVALID`.
- `SIRCOM_STEP_INVALID`.
- `SIRCOM_RETRY_NOT_ALLOWED`.

Préconditions critiques sur lot vide :

- `SIRCOM_EXCEL_DIAGNOSTIC_NOT_READY`.
- `SIRCOM_IMAGE_INSPECTION_NOT_READY`.
- `SIRCOM_IMAGE_MATCHING_NOT_READY`.
- `SIRCOM_MAPPING_DIAGNOSTIC_NOT_READY`.
- `SIRCOM_SORT_NORMALIZATION_NOT_READY`.
- `SIRCOM_CSV_SORT_NOT_VALIDATED`.
- `SIRCOM_CSV_EXPORT_PREREQUISITES_MISSING`.
- `SIRCOM_REPORTS_NOT_READY`.
- `SIRCOM_PACKAGE_NOT_READY`.
- `SIRCOM_PACKAGE_PREREQUISITE_MISSING`.

Codes métier couverts par les tests ciblés existants :

- upload Excel : `SIRCOM_EXCEL_EXTENSION_UNSUPPORTED`,
  `SIRCOM_EXCEL_TOO_LARGE`, `SIRCOM_EXCEL_UNREADABLE`.
- upload images : `SIRCOM_IMAGE_ZIP_EXTENSION_UNSUPPORTED`,
  `SIRCOM_IMAGE_ZIP_SIGNATURE_INVALID`, `SIRCOM_IMAGE_ZIP_TOO_LARGE`,
  `SIRCOM_IMAGE_ZIP_NO_TREATABLE_IMAGE`,
  `SIRCOM_IMAGE_ZIP_ENCRYPTED_ENTRY`.
- mapping : `SIRCOM_MAPPING_CSV_HEADER_COLLISION`,
  `SIRCOM_MAPPING_IDEMPOTENCY_REUSED`,
  `SIRCOM_MAPPING_PROFILE_INCOMPATIBLE`.
- package : `SIRCOM_PACKAGE_WARNINGS_DECISION_REQUIRED`,
  `SIRCOM_PACKAGE_BLOCKERS_OPEN`, `SIRCOM_IDEMPOTENCY_KEY_CONSUMED`.

### Préconditions à préserver

- Les uploads Excel et images vérifient l'existence et la mutabilité du lot
  avant de valider le fichier.
- Les routes de lecture d'artefacts métier retournent `409` avec un code stable
  quand l'étape amont n'est pas prête.
- Les validations humaines mapping, tri et aperçu CSV restent idempotentes via
  `X-Idempotency-Key`.
- Les opérations longues ne sont pas exécutées dans la requête HTTP : uploads,
  retry, résolutions images et package retournent un job ou planifient un job.
- Les erreurs API restent structurées sous `{"error": {"code", "message", ...}}`
  et ne doivent pas exposer de chemin local.

## Livraison

- Aucun refactor de `sircom2026/api/lots.py` n'a été réalisé.
- `tests/test_lots_api.py` ajoute une table de contrat du router lots avec
  méthodes, chemins et statuts nominaux.
- `tests/test_lots_api.py` ajoute un test des codes d'erreur structurés des
  routes critiques sur lot vide : diagnostic Excel, inspection images, matching,
  mapping, tri, CSV, rapports, package et retry.
- Les tests existants `test_excel_upload`, `test_image_upload`,
  `test_package` et `test_workflow_failure_paths` restent les preuves ciblées
  des préconditions spécialisées et du workflow.

Preuves exécutées le 2026-07-23 :

- `uv run --frozen --extra test pytest tests/test_lots_api.py tests/test_api_access_errors.py tests/test_image_upload.py tests/test_excel_upload.py tests/test_package.py tests/test_workflow_failure_paths.py -q` :
  62 tests passés.
- `uv run --frozen --extra test pytest -q` : 229 tests passés, 4 sautés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
