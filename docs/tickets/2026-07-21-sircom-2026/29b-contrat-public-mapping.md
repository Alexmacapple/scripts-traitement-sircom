# 29B - Contrat public `mapping.py`

Statut : `done`

Dépend de : aucun, peut commencer immédiatement.

À construire : documenter et verrouiller le contrat public du mapping avant
tout nouveau découpage de `sircom2026/mapping.py`.

## Énoncé du problème

`mapping.py` concentre mapping par défaut, brouillons, validation humaine,
profils et noms CSV. Un découpage sans contrat peut casser un détail métier
visible : colonnes exportées, provenance, profils ou invalidation aval.

## Solution

Identifier les fonctions et objets utilisés hors du module, puis ajouter des
tests de contrat sur les comportements qui doivent rester stables.

## Critères d'acceptation

- [x] Les entrées publiques de mapping utilisées par l'API et le rendu web sont
      listées.
- [x] Le contrat de mapping par défaut conserve la provenance onglet, lettre,
      nom original, nom CSV et statut exporté.
- [x] Le contrat de validation conserve l'invalidation aval attendue.
- [x] Le contrat de profils conserve brouillon, sauvegarde et réapplication.
- [x] Les cas `id_dossier`, colonnes images, colonnes vides et noms CSV courts
      sont couverts.
- [x] Aucun refactor de structure n'est réalisé dans ce ticket.
- [x] `tests.test_mapping`, `tests.test_csv_preview` et
      `tests.test_invalidation` passent.

## Hors périmètre

- Modifier les règles de nommage CSV.
- Modifier l'ergonomie de l'écran mapping.
- Déplacer des fonctions hors de `mapping.py`.

## Garde-fous LLM

- Ne pas transformer le contrat en documentation exhaustive de toutes les
  fonctions privées.
- Verrouiller les comportements observables, pas l'implémentation interne.
- Ne pas changer les clés persistées pour les franciser ; la traduction reste
  dans la couche UI.

## Preuve attendue

- tests de contrat mapping ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Contrat public à préserver en 31

### Importeurs applicatifs

- `sircom2026/api/lots.py` importe `MappingError`,
  `apply_profile_as_draft`, `get_mapping_payload`, `save_mapping_draft`,
  `save_profile_from_validated_mapping` et `validate_mapping`.
- `sircom2026/app.py` importe `get_mapping_payload` pour le rendu web.
- `sircom2026/web_context.py` et `sircom2026/web_ui.py` importent
  `MappingError` pour l'affichage d'erreurs mapping.
- `sircom2026/transform.py`, `sircom2026/reports.py` et
  `sircom2026/package.py` consomment `MAPPING_STEP_KEY` ou les artefacts de
  mapping validés.

### Constantes publiques

- `MAPPING_STEP_KEY = "mapping"`.
- `FUSION_STEP_KEY = "fusion_multi_onglets"`.
- `MAPPING_RULES_VERSION = "mapping-v1"`.
- `MAPPING_SCHEMA_VERSION = 1`.
- `MAPPING_MIME_TYPE = "application/json"`.
- `MAPPING_STATUS_VALUES = {"exporte", "supprime"}`.
- `SYSTEM_COLUMN_IDS = ("system:imageid", "system:@pathimg")`.
- `MAPPING_LOGICAL_ROLES` contient `id_dossier`, `date`, `region`,
  `departement`, `nom_image_source`, `siret`, `telephone`, `code_postal`,
  `code_administratif` et `texte`.

### Types et fonctions publiques

- `MappingOperationResult` : porte `mapping`, `artifact`, `lot` et
  `invalidated_steps`.
- `PersistedMappingSnapshot` : porte `artifact` et `created`.
- `MappingError` : erreur métier avec `status_code`, `code`, `message` et
  `details`.
- `get_mapping_payload(repositories, settings=..., lot_id=...)` : expose le
  mapping courant ou le mapping par défaut, avec les profils compatibles et
  incompatibles.
- `build_default_mapping_from_current_diagnostic(...)` : construit le mapping
  par défaut depuis le diagnostic Excel courant.
- `save_mapping_draft(...)` : persiste un brouillon et remet l'étape mapping en
  validation humaine.
- `validate_mapping(...)` : persiste le mapping validé, enregistre la décision
  humaine, invalide l'aval et enqueue `fusion_multi_onglets`.
- `save_profile_from_validated_mapping(...)` : transforme le mapping validé
  courant en profil global.
- `apply_profile_as_draft(...)` : applique un profil compatible comme brouillon
  seulement, jamais comme validation silencieuse.
- `read_current_mapping_artifact(...)` : lit le dernier artefact mapping courant
  et lève une erreur métier si l'artefact est indisponible.
- `mapping_from_submission(...)`, `mapping_validation_errors(...)`,
  `apply_profile_to_default_mapping(...)`, `profile_compatibility(...)` et
  `profile_from_mapping(...)` restent des points de contrat utiles au refactor.
- `MappingProfileStore` conserve le stockage disque des profils dans
  `profiles/mapping`.

### Payload mapping

Le payload racine doit rester un dictionnaire JSON avec au moins :

- `schema_version`, `rules_version`, `source`,
  `structural_fingerprint`, `source_diagnostic_artifact_id` ;
- `sheets[]` avec `name`, `header_row` et `columns_count` ;
- `columns[]`, en ordre source, avec les colonnes système ajoutées juste après
  la première colonne `id_dossier` exportée.

Chaque colonne publique conserve au moins :

- identité et provenance : `id`, `source_sheet`, `source_column_index`,
  `source_column_letter`, `source_header` ;
- décision : `status`, `csv_name`, `default_csv_name`,
  `suppression_reason`, `output_position` ;
- méta : `system`, `locked`, `logical_role`.

Contrats métier figés :

- toutes les colonnes source des onglets utiles sont sélectionnées par défaut,
  y compris une colonne entièrement vide ; la suppression des colonnes vides se
  fait plus tard dans le flux CSV ;
- une seule colonne `id_dossier` est exportée ; les autres servent à la fusion
  interne, restent verrouillées et portent une raison de suppression ;
- `imageid` et `@pathimg` sont des colonnes système verrouillées, exportées
  juste après `id_dossier` ;
- hors exceptions `id_dossier`, `imageid` et `@pathimg`, les noms CSV exportés
  restent courts, nettoyés et limités à 10 caractères.

### Profils

Un profil de mapping conserve :

- `id`, `name`, `version`, `rules_version`, `structural_fingerprint` ;
- `sheets`, `headers`, `letters`, `logical_roles`, `columns` ;
- `last_used_at`.

La compatibilité reste calculée par version de schéma, version de règles et
fingerprint structurel. Un profil compatible est listé et peut être appliqué
comme brouillon ; un profil incompatible est listé comme incompatible et refusé
à l'application.

### Codes d'erreur publics

- `SIRCOM_MAPPING_DIAGNOSTIC_NOT_READY`.
- `SIRCOM_MAPPING_DIAGNOSTIC_BLOCKED`.
- `SIRCOM_MAPPING_SOURCE_HEADERS_MISSING`.
- `SIRCOM_LOT_NOT_MUTABLE`.
- `SIRCOM_MAPPING_VALIDATED_NOT_FOUND`.
- `SIRCOM_MAPPING_PROFILE_NOT_FOUND`.
- `SIRCOM_MAPPING_PROFILE_INCOMPATIBLE`.
- `SIRCOM_MAPPING_STRUCTURE_MISMATCH`.
- `SIRCOM_MAPPING_PAYLOAD_INVALID`.
- `SIRCOM_MAPPING_COLUMNS_MISMATCH`.
- `SIRCOM_MAPPING_STATUS_INVALID`.
- `SIRCOM_MAPPING_ROLE_INVALID`.
- `SIRCOM_MAPPING_NO_BUSINESS_COLUMN`.
- `SIRCOM_MAPPING_CSV_NAME_MISSING`.
- `SIRCOM_MAPPING_CSV_HEADER_COLLISION`.
- `SIRCOM_MAPPING_ID_DOSSIER_INVALID`.
- `SIRCOM_MAPPING_IDEMPOTENCY_REUSED`.
- `SIRCOM_MAPPING_COMMIT_REJECTED`.
- `SIRCOM_MAPPING_ARTIFACT_UNAVAILABLE`.
- `SIRCOM_MAPPING_ARTIFACT_INVALID`.

## Livraison

- Aucun refactor de `sircom2026/mapping.py` n'a été réalisé.
- `tests/test_mapping.py` ajoute un test explicite des entrées publiques,
  constantes, rôles, statuts et dataclasses de mapping.
- Le test de mapping par défaut vérifie maintenant les champs publics de chaque
  colonne, les colonnes système images, la colonne source vide exportée par
  défaut, le rôle image source et la limite de 10 caractères des noms CSV.
- Le test de profils vérifie que les colonnes sauvegardées conservent les
  champs de décision nécessaires à la réapplication.
- La revue Spec a demandé de compléter la couverture de `MAPPING_STEP_KEY`,
  `FUSION_STEP_KEY`, des champs racine `schema_version`,
  `source_diagnostic_artifact_id`, `sheets[]` et des attributs publics de
  `MappingError` ; ces points sont maintenant vérifiés par test.

Preuves exécutées le 2026-07-23 :

- `uv run --frozen --extra test pytest tests/test_mapping.py tests/test_csv_preview.py tests/test_invalidation.py -q` :
  20 tests passés.
- `uv run --frozen --extra test pytest -q` : 227 tests passés, 4 sautés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
