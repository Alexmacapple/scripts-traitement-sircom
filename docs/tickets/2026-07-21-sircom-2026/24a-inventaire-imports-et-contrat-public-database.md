# 24A - Inventaire imports et contrat public database.py

Statut : `done`

Dépend de : 24.

Livré : contrat utilisé comme entrée de la tranche 24B, première
extraction repository/database, avec compatibilité des imports.

## État de livraison au 2026-07-23

Inventaire livré par `a0dfd9f docs: ajouter contrat database 24a`.

La tranche 24B qui dépendait de ce contrat est également livrée par
`81ce0b7 refactor: extraire repositories database`. Les imports publics de
`sircom2026.database` restent compatibles via la façade historique.

Preuves principales :

- `uv run --frozen --extra test pytest tests/test_database.py tests/test_state.py tests/test_invalidation.py tests/test_worker.py -q` :
  `52 passed`.
- `uv run --frozen --extra test pytest -q -rs` : `221 passed, 4 skipped`.
- `uv run --frozen --extra test ruff check .` : `All checks passed!`.

## Objectif

Produire l'inventaire des usages publics de `sircom2026.database` avant tout
déplacement de code. Cette tranche ne refactorise pas encore `database.py` :
elle évite que 24B transforme un déplacement mécanique en rupture d'import, de
transaction ou de contrat repository.

## Inventaire des imports publics

Noms importés depuis `sircom2026.database` dans `sircom2026/` et `tests/` :

- `ACTIVE_JOB_STATUSES`
- `Database`
- `LOT_WRITE_BLOCKED_STATUSES`
- `PROBLEM_SEVERITIES`
- `Repositories`
- `SCHEMA_VERSION`
- `STEP_STATUSES`
- `SchemaVersionError`
- `TECHNICAL_EVENT_PAYLOAD_KEYS`
- `connect_sqlite`
- `migrate_database`

Fichiers applicatifs qui importent `Database` :

- `sircom2026/api/artifacts.py`
- `sircom2026/api/dependencies.py`
- `sircom2026/api/lots.py`
- `sircom2026/api/storage.py`
- `sircom2026/app.py`
- `sircom2026/purge.py`
- `sircom2026/worker.py`
- `sircom2026/worker_runner.py`

Fichiers applicatifs qui importent `Repositories` :

- `sircom2026/api/artifacts.py`
- `sircom2026/artifacts.py`
- `sircom2026/csv_contract.py`
- `sircom2026/csv_preview.py`
- `sircom2026/excel_diagnostic_pipeline.py`
- `sircom2026/excel_upload.py`
- `sircom2026/image_matching.py`
- `sircom2026/images.py`
- `sircom2026/invalidation.py`
- `sircom2026/lots.py`
- `sircom2026/mapping.py`
- `sircom2026/purge.py`
- `sircom2026/reports.py`
- `sircom2026/sorting.py`
- `sircom2026/state.py`
- `sircom2026/transform.py`
- `sircom2026/worker.py`

## Contrat public à préserver en 24B

`sircom2026.database` doit rester une façade importable pendant l'extraction.
Les noms listés dans l'inventaire doivent continuer à être importables depuis
ce module, même si leur implémentation bouge vers des modules internes.

Contrat `Database` :

- constructeur `Database(path: Path, busy_timeout_ms: int = 5000)` ;
- `connect()` retourne une connexion SQLite configurée ;
- `migrate()` applique les migrations ;
- `session()` fournit un `Repositories`, valide la transaction ouverte en fin
  de bloc, annule sur exception et ferme la connexion ;
- `transaction()` ouvre `BEGIN IMMEDIATE`, fournit un `Repositories`, valide en
  fin de bloc, annule sur exception et ferme la connexion.

Contrat `connect_sqlite` :

- crée le répertoire parent de la base si besoin ;
- met en place `row_factory`, `PRAGMA foreign_keys = ON`,
  `PRAGMA busy_timeout` et tente `PRAGMA journal_mode = WAL` ;
- conserve le `warning_handler` optionnel pour le cas où WAL n'est pas
  disponible.

Contrat `migrate_database` :

- refuse une version de schéma plus récente que `SCHEMA_VERSION` ;
- applique les migrations dans l'ordre ;
- valide la structure attendue ;
- laisse `PRAGMA user_version` aligné sur `SCHEMA_VERSION`.

Contrat `Repositories` :

- expose la connexion brute via `repositories.connection` ;
- expose les propriétés `lots`, `steps`, `jobs`, `artifacts`, `events`,
  `problems` et `purge_traces` ;
- chaque propriété retourne un repository lié à la même connexion.

Le contrat inclut temporairement les classes concrètes suivantes, même si elles
ne sont pas importées directement hors de `database.py` aujourd'hui :

- `LotsRepository`
- `StepsRepository`
- `JobsRepository`
- `ArtifactsRepository`
- `EventsRepository`
- `ProblemsRepository`
- `PurgeTracesRepository`

## Méthodes repository appelées

Méthodes appelées sur `repositories.lots` :

- `count`
- `create`
- `get`
- `get_by_idempotency_key`
- `get_required`
- `list`
- `list_deleted_ready_for_purge`
- `mark_deleted`
- `mark_purged`
- `refresh_artifact_counters`
- `request_cancel`
- `update_status`

Méthodes appelées sur `repositories.steps` :

- `create`
- `get_by_lot_key`
- `get_required`
- `list_for_lot`
- `mark_invalidated`
- `prepare_run`
- `set_output_fingerprint`
- `set_summary`
- `update_status`

Méthodes appelées sur `repositories.jobs` :

- `acquire_next`
- `cancel_active_for_step`
- `cancel_queued_for_lot`
- `count_active_for_lot`
- `count_processing_for_lot`
- `create`
- `create_owned_running`
- `expire_stale_leases`
- `finish_owned`
- `get`
- `get_active_for_step`
- `get_by_idempotency_key`
- `get_committable_by_run`
- `get_required`
- `heartbeat`
- `mark_running`
- `request_cancel_for_lot`
- `update_progress`
- `update_status`

Méthodes appelées sur `repositories.artifacts` :

- `create`
- `get`
- `get_for_lot`
- `get_for_step_run_role`
- `get_required`
- `list_all`
- `mark_obsolete_for_steps`
- `update_status`

Méthodes appelées sur `repositories.events` :

- `create`
- `get_required`
- `list_for_lot`
- `update_payload`

Méthodes appelées sur `repositories.problems` :

- `count_open_by_severity`
- `count_open_for_step_by_severity`
- `create`
- `get_required`
- `list_for_lot`
- `mark_open_obsolete_for_steps`
- `update_status`

Méthodes appelées sur `repositories.purge_traces` :

- `get_by_lot_id_hash`
- `latest`
- `prune_before`
- `upsert`

## Frictions et risques pour 24B

- `repositories.connection` est encore utilisé directement dans `sircom2026/app.py`,
  `sircom2026/csv_preview.py`, `sircom2026/mapping.py`,
  `sircom2026/purge.py` et plusieurs tests. 24B ne doit donc pas masquer la
  connexion sans migration explicite de ces usages.
- Les constantes métier restent importées depuis `sircom2026.database`.
  Déplacer les repositories sans façade de compatibilité casserait des modules
  qui ne touchent pas directement SQLite.
- `Database.session()` et `Database.transaction()` portent une sémantique de
  validation, annulation et fermeture. Extraire les repositories ne doit pas
  déplacer cette responsabilité vers les appelants.
- Les classes concrètes de repository peuvent être déplacées, mais `database.py`
  doit les réexporter pendant la transition si des tests ou agents futurs les
  importent depuis le module historique.

## Critères d'acceptation de 24B

- [x] Tous les imports listés dans ce ticket restent valides depuis
      `sircom2026.database`.
- [x] Les propriétés de `Repositories` exposent les mêmes noms et utilisent la
      même connexion SQLite.
- [x] `Database.session()` et `Database.transaction()` conservent leur
      comportement de transaction, rollback et fermeture de connexion.
- [x] Aucune constante métier importée depuis `sircom2026.database` n'est
      renommée.
- [x] Les tests ciblés `tests/test_database.py`, `tests/test_state.py`,
      `tests/test_invalidation.py` et `tests/test_worker.py` passent après
      extraction.
- [x] `uv run --frozen --extra test pytest -q` passe avant commit final de 24B.

## Preuve d'inventaire

Inventaire établi depuis :

- extraction AST des imports `from sircom2026.database import ...` dans
  `sircom2026/` et `tests/` ;
- extraction AST des méthodes de classes dans `sircom2026/database.py` ;
- extraction AST des appels `repositories.<repo>.<method>(...)` dans
  `sircom2026/` et `tests/` ;
- lecture ciblée de `sircom2026/database.py` autour de `Database`,
  `connect_sqlite`, `migrate_database` et `Repositories`.

Limite : cette tranche documente le contrat observé au 2026-07-23. Elle ne
prouve pas encore que l'extraction 24B sera sans régression ; cette preuve devra
venir des tests ciblés et de la suite complète après déplacement de code.

---

Parent : [24 - Refactorisation progressive des fichiers volumineux](24-refactorisation-progressive-des-fichiers-volumineux.md)
