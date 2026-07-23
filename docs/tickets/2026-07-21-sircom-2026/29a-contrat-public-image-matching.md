# 29A - Contrat public `image_matching.py`

Statut : `done`

Dépend de : aucun, peut commencer immédiatement.

À construire : documenter et verrouiller le contrat public du matching images
avant tout nouveau découpage de `sircom2026/image_matching.py`.

## Énoncé du problème

`image_matching.py` reste volumineux et porte à la fois règles de matching,
résolutions manuelles, génération d'artefacts et orchestration worker. Un
refactor sans contrat peut passer les tests généraux tout en modifiant une règle
implicite importante pour le package final.

## Solution

Créer un contrat court des fonctions, erreurs, statuts et artefacts publics à
préserver. Ajouter ou renforcer les tests de contrat sur les cas critiques avant
de déplacer du code.

## Critères d'acceptation

- [x] Les entrées publiques de matching utilisées par l'API, le worker, les
      rapports et le package sont listées.
- [x] Les statuts de binding images et leurs libellés attendus sont listés.
- [x] Les cas exact, tolérant, ambigu, source dupliquée, image manquante et
      collision de nom final sont couverts par tests.
- [x] Les exceptions métier et codes d'erreur attendus sont couverts.
- [x] Aucun refactor de structure n'est réalisé dans ce ticket.
- [x] `tests.test_image_matching`, `tests.test_package` et `tests.test_reports`
      passent.

## Hors périmètre

- Déplacer des fonctions hors de `image_matching.py`.
- Changer les règles de matching.
- Changer les noms finaux `dossier-{id-normalise}.jpg`.

## Garde-fous LLM

- Ce ticket prépare le refactor, il ne le fait pas.
- Si une règle semble incorrecte, la noter comme dette séparée au lieu de la
  corriger.
- Les clés techniques persistées peuvent rester en anglais côté API et base ;
  les libellés visibles restent en français.

## Preuve attendue

- tests de contrat matching images ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Contrat public à préserver en 30

### Importeurs applicatifs

- `sircom2026/api/lots.py` importe `ImageMatchingNotReady`,
  `ImageResolutionError`, `get_persisted_image_matching` et
  `save_image_resolutions`.
- `sircom2026/worker.py` importe `image_matching_input_payload`.
- `sircom2026/worker_runner.py` importe `run_image_matching_job`.
- `sircom2026/reports.py` importe `MATCHING_IMAGES_STEP_KEY`,
  `MATCHING_ARTIFACT_ROLE` et `PROCESSED_IMAGES_ARTIFACT_ROLE`.
- `sircom2026/package.py` importe `EXPORT_IMAGES_FOLDER`,
  `MATCHING_IMAGES_STEP_KEY`, `MATCHING_ARTIFACT_ROLE` et
  `PROCESSED_IMAGES_ARTIFACT_ROLE`.

### Constantes publiques

- `MATCHING_IMAGES_STEP_KEY = "matching_images"`.
- `MATCHING_ARTIFACT_ROLE = "result"`.
- `PROCESSED_IMAGES_ARTIFACT_ROLE = "processed_images"`.
- `MATCHING_RULES_VERSION = "image-matching-v1"`.
- `MATCHING_SCHEMA_VERSION = 1`.
- `MANUAL_RESOLUTIONS_RULES_VERSION = "image-manual-resolutions-v1"`.
- `EXPORT_IMAGES_FOLDER = "export-jpg-resize"`.
- `FINAL_IMAGE_MAX_WIDTH_PX = 350`.
- `FINAL_IMAGE_JPEG_QUALITY = 100`.
- `FINAL_IMAGE_DPI = 300`.
- `MATCHABLE_IMAGE_SOURCE_ROLE = "nom_image_source"`.

### Types et fonctions publiques

- `PersistedImageMatching` : porte `matching`, `artifact` et
  `processed_images_artifact`.
- `ImageResolutionResult` : porte le job relancé, le lot, les étapes invalidées
  et les compteurs d'artefacts/jobs obsolètes.
- `ImageMatchingNotReady` : signal d'absence d'artefact matching courant.
- `ImageResolutionError` : erreur métier avec `status_code`, `code`, `message`
  et `details`.
- `image_matching_input_payload(repositories, lot_id=...)` : payload
  fingerprinté utilisé par le worker pour l'idempotence de l'étape.
- `enqueue_image_matching_job(repositories, lot_id=..., idempotency_key=...)` :
  relance idempotente de l'étape `matching_images`.
- `run_image_matching_job(context, settings=...)` : handler worker de
  l'association et du zip d'images traitées.
- `build_image_matching_payload(...)` : construit le JSON métier du matching
  depuis la normalisation, l'inspection et les résolutions manuelles.
- `build_processed_images_zip(source_zip_path, matching_payload)` : produit le
  zip `export-jpg-resize/` et enrichit les bindings traités.
- `image_matching_problems(matching)` : transforme les compteurs de matching en
  problèmes structurés.
- `get_persisted_image_matching(repositories, settings=..., lot_id=...)` :
  expose le matching courant et l'artefact zip traité courant.
- `save_image_resolutions(...)` : valide les choix manuels, invalide l'aval et
  relance `matching_images`.
- `read_manual_image_resolutions(repositories, lot_id=...)` : lit le résumé de
  résolutions persistées.

### Payload matching

Le payload racine doit rester un dictionnaire JSON avec au moins :

- provenance : `schema_version`, `rules_version`,
  `source_normalization_artifact_id`, `source_inspection_artifact_id`,
  `source_image_zip_artifact_id`, `source_image_zip_sha256`,
  `rules_fingerprint` ;
- réglages images : `image_root`, `final_folder`, `final_width_max_px`,
  `final_jpeg_quality`, `final_dpi` ;
- données : `manual_resolutions`, `source_image_columns`, `bindings`,
  `unreferenced_images` ;
- compteurs : `rows_count`, `bindings_count`, `matched_count`,
  `missing_count`, `ambiguous_count`, `conversion_failed_count`,
  `fallback_count`, `tolerant_count`, `processed_images_count`,
  `unreferenced_count` ;
- décisions : `blocking` et `has_warnings`.

Chaque binding public doit conserver au moins :

- `id_dossier`, `original_filenames`, `source_name`, `source_artifact_id`,
  `source_zip_fingerprint`, `source_image_zip_sha256` ;
- `rules_version`, `rules_fingerprint` ;
- `imageid`, `final_name`, `final_sha256`, `pathimg` ;
- `status`, `match_level`, `fallback_used`, `manual_resolution` ;
- `candidates` et `suggestions`.

### Statuts et libellés UI

Statuts de binding :

| Statut technique | Libellé visible | Effet attendu |
|---|---|---|
| `matched` | `Associée` | Image source retenue ; le zip traité peut renseigner `final_sha256` et `pathimg`. |
| `missing` | `Manquante` | `imageid` reste calculé, `pathimg` reste vide, alerte non bloquante. |
| `ambiguous` | `À résoudre` | Bloque le matching courant ; `candidates` ou `suggestions` guident le choix manuel. |
| `conversion_failed` | `Conversion échouée` | Image retenue mais conversion JPG impossible ; `pathimg` reste vide. |

Images non référencées : `unreferenced_images[].status = "ignored"` avec
`reason = "not_referenced"`. Ce statut n'est pas un statut de binding.

Niveaux de matching publics :

- `none` : `Aucune correspondance`.
- `final_name_collision` : `Collision de nom final`.
- `manual_invalid` : `Choix manuel invalide`.
- `manual` : `Choix manuel`.
- `original_exact` : `Nom source exact`.
- `original_exact_stem` : `Nom source exact sans extension`.
- `original_tolerant` : `Nom source proche`.
- `id_fallback_exact` : `ID dossier exact de secours`.
- `id_fallback_exact_final_name` : `ID dossier exact de secours par nom final`.
- `id_fallback_tolerant` : `ID dossier proche de secours`.
- `id_fallback_tolerant_final_name` : `ID dossier proche de secours par nom final`.
- `partial_suggestion` : `Suggestion partielle`.
- `source_duplicate` : `Image source utilisée plusieurs fois`.

### Codes d'erreur et problèmes

Codes de problèmes issus de `image_matching_problems` :

- `SIRCOM_IMAGE_MATCHING_AMBIGUOUS`.
- `SIRCOM_IMAGE_MATCHING_MISSING`.
- `SIRCOM_IMAGE_MATCHING_UNREFERENCED`.
- `SIRCOM_IMAGE_MATCHING_ID_FALLBACK_USED`.
- `SIRCOM_IMAGE_MATCHING_TOLERANCE_USED`.
- `SIRCOM_IMAGE_CONVERSION_FAILED`.

Codes d'erreur publics :

- `SIRCOM_IMAGE_MATCHING_NOT_READY` : exposition API du matching non disponible.
- `SIRCOM_LOT_NOT_MUTABLE` : lot fermé ou non modifiable.
- `SIRCOM_IDEMPOTENCY_KEY_CONSUMED` : clé de relance déjà consommée.
- `SIRCOM_IMAGE_RESOLUTION_EMPTY` : aucune résolution fournie.
- `SIRCOM_IMAGE_RESOLUTION_DOSSIER_UNKNOWN` : dossier inconnu.
- `SIRCOM_IMAGE_RESOLUTION_SOURCE_UNKNOWN` : image source inconnue.
- `SIRCOM_IMAGE_RESOLUTION_SOURCE_DUPLICATED` : même source affectée plusieurs
  fois.
- `SIRCOM_IMAGE_RESOLUTION_NORMALIZATION_NOT_READY` : normalisation indisponible.
- `SIRCOM_IMAGE_RESOLUTION_INSPECTION_NOT_READY` : inspection indisponible ou
  bloquante.

## Livraison

- Aucun refactor de `sircom2026/image_matching.py` n'a été réalisé.
- `source_duplicate`, déjà persisté par le matching, reçoit un libellé visible
  français pour éviter un niveau non traduit dans l'interface.
- `tests/test_image_matching.py` ajoute un test de stabilité des statuts,
  libellés visibles, niveaux de matching et codes de problèmes.
- `tests/test_image_matching.py` ajoute un test des codes publics levés par
  `save_image_resolutions`.

Preuves exécutées le 2026-07-23 :

- `uv run --frozen --extra test pytest tests/test_image_matching.py -q` :
  13 tests passés.
- `uv run --frozen --extra test pytest tests/test_image_matching.py tests/test_package.py tests/test_reports.py -q` :
  OK.
- `uv run --frozen --extra test pytest -q` : OK.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
