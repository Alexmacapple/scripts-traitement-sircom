# Contrat exécution, stockage et worker Sircom 2026

Date : 2026-07-21

## Sources

- `docs/specs/2026-07-21-orchestration-sircom-2026.md`
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`
- `docs/audits/2026-07-21-synthese-verification-globale-sircom-2026.md`
- tickets 03, 04, 05, 06, 07, 08

## Problème

Les revues GLM/SOL/Codex ont montré que le découpage était bon mais que le
schéma, les leases, l'idempotence, la réconciliation disque/SQLite et
l'invalidation aval devaient être fixés avant implémentation.

## Paramètres V1

| Variable | Valeur V1 | Rôle |
|---|---:|---|
| `SIRCOM_MAX_ACTIVE_JOBS` | `1` | Un seul job local actif. |
| `SIRCOM_WORKER_POLL_SECONDS` | `2` | Attente entre deux acquisitions. |
| `SIRCOM_WORKER_LEASE_TTL_SECONDS` | `300` | Durée maximale d'un lease sans heartbeat. |
| `SIRCOM_WORKER_HEARTBEAT_SECONDS` | `30` | Cadence de heartbeat. |
| `SIRCOM_SQLITE_BUSY_TIMEOUT_MS` | `5000` | Attente SQLite avant erreur de verrou. |
| `SIRCOM_ARTIFACT_PENDING_TTL_SECONDS` | `3600` | Durée avant réconciliation d'un artefact pending. |

Le ticket 01 expose les variables déjà listées dans son périmètre. Les variables
ci-dessus sont ajoutées par les tickets propriétaires quand les modules worker
et store apparaissent.

## Schéma SQLite minimal normatif

Toutes les tables ont `id`, `created_at`, `updated_at`.

`lots` :

- `status` ;
- `title` optionnel ;
- `active_run_id` optionnel ;
- `cancel_requested_at` ;
- `delete_requested_at` ;
- `deleted_at` ;
- `purge_requested_at` ;
- compteurs techniques non sensibles.

`etapes` :

- `lot_id` ;
- `step_key` ;
- `status` ;
- `current_run_id` ;
- `input_fingerprint` ;
- `output_fingerprint` ;
- `progress_current` ;
- `progress_total` ;
- `started_at`, `finished_at`, `invalidated_at` ;
- contrainte unique `(lot_id, step_key)`.

`jobs` :

- `lot_id` ;
- `step_key` ;
- `status` ;
- `run_id` ;
- `idempotency_key` ;
- `lease_owner` ;
- `lease_version` entier ;
- `lease_until` ;
- `heartbeat_at` ;
- `attempt` ;
- `cancel_requested_at` ;
- `started_at`, `finished_at` ;
- contrainte unique `(lot_id, step_key, idempotency_key)`.

`artefacts` :

- `lot_id` ;
- `step_key` ;
- `run_id` ;
- `status` parmi `pending`, `committed`, `obsolete`, `deleted`,
  `quarantined` ;
- `kind` et `role` ;
- `relative_path` ;
- `sha256` ;
- `size_bytes` ;
- `schema_version` ;
- `committed_at`, `obsoleted_at`, `deleted_at`, `quarantined_at`.

`evenements` :

- `lot_id` ;
- `step_key` optionnel ;
- `run_id` optionnel ;
- `event_type` ;
- `payload_json` sans valeur métier sensible.

`problemes` :

- `lot_id` ;
- `step_key` ;
- `run_id` optionnel ;
- `severity` parmi `bloquant`, `alerte`, `information` ;
- `code` stable ;
- `title`, `cause`, `message`, `action`, `location_json`, `technical_json` ;
- `status` parmi `open`, `resolved`, `obsolete`.

## SQLite

- Activer `PRAGMA foreign_keys = ON`.
- Essayer `journal_mode = WAL`; si indisponible, journal par défaut accepté avec
  événement technique.
- Appliquer `busy_timeout` depuis `SIRCOM_SQLITE_BUSY_TIMEOUT_MS`.
- Les acquisitions de job et commits d'artefacts utilisent une transaction
  courte `BEGIN IMMEDIATE`.
- Les migrations sont idempotentes et versionnées dans `schema_migrations`.

## Statuts

Lots :

- `brouillon` ;
- `en_cours` ;
- `action_requise` ;
- `bloque` ;
- `termine` ;
- `termine_avec_alertes` ;
- `echoue` ;
- `annule` ;
- `supprime` ;
- `purge`.

Étapes :

- `non_demarre` ;
- `pret` ;
- `en_cours` ;
- `action_requise` ;
- `bloque` ;
- `termine` ;
- `termine_avec_alertes` ;
- `echoue` ;
- `ignore` ;
- `annule` ;
- `invalide`.

Jobs :

- `queued` ;
- `leased` ;
- `running` ;
- `succeeded` ;
- `failed` ;
- `canceled` ;
- `expired`.

## Matrice de transitions

| Événement | Effet étape | Effet lot |
|---|---|---|
| Création lot | étapes `non_demarre` | `brouillon` |
| Upload accepté | étape cible `pret` ou job `queued`, aval `invalide` | `en_cours` ou `action_requise` |
| Job acquis | `en_cours` | `en_cours` |
| Job réussi sans alerte | `termine` | agrégé depuis étapes |
| Job réussi avec alertes | `termine_avec_alertes` | `termine_avec_alertes` si aucune étape bloquante |
| Validation humaine attendue | `action_requise` | `action_requise` |
| Blocage métier corrigible | `bloque` | `bloque` |
| Exception technique | `echoue` | `echoue` |
| Retry utilisateur | nouveau `run_id`, étape `pret`, aval `invalide` | `en_cours` |
| Invalidation par nouvel input | étape aval `invalide`, artefacts aval `obsolete` | statut recalculé |
| Annulation utilisateur | étape en cours `annule`, job `canceled` | `annule` |
| DELETE lot | tombstone, jobs actifs annulés | `supprime` puis purge physique par ticket 23 |

Un lot final est `termine` seulement si toutes les étapes obligatoires sont
`termine`, `termine_avec_alertes` ou `ignore` selon les règles métier, sans
problème `bloquant` ouvert.

## Worker

- Le worker est local et intégré au processus applicatif V1 ou lancé par une
  commande locale documentée.
- Il acquiert un job `queued` ou `expired` avec `lease_until < now`.
- L'acquisition incrémente `lease_version`, pose `lease_owner`, `lease_until`,
  `heartbeat_at` et conserve le `run_id` du job.
- Le heartbeat prolonge le lease uniquement si `run_id`, `lease_owner` et
  `lease_version` correspondent encore.
- Un worker qui perd son lease ne peut plus committer.
- L'arrêt gracieux termine la sous-opération courante, marque le job annulé si
  l'annulation a été demandée, sinon libère ou laisse expirer le lease.

## Fencing et commits tardifs

Tout commit d'étape, problème ou artefact vérifie en transaction :

- le `run_id` courant ;
- le `lease_version` courant pour les écritures worker ;
- le statut non annulé et non supprimé du lot ;
- le fingerprint d'entrée attendu si l'étape dépend d'artefacts amont.

Si la vérification échoue, l'écriture est refusée, un événement technique est
ajouté et l'artefact disque éventuel est placé en quarantaine ou supprimé.

## Store d'artefacts

Protocole de commit :

1. écrire dans un chemin temporaire sous le lot ;
2. calculer taille et SHA-256 ;
3. créer ou mettre à jour la ligne `artefacts` en `pending` ;
4. promouvoir par renommage atomique dans l'emplacement final ;
5. valider en base `committed` dans la même section critique logique ;
6. rendre téléchargeable seulement après statut `committed`.

Le `relative_path` est interne et ne sort jamais dans l'API publique. Les
téléchargements passent par `artifact_id`.

## Réconciliation au démarrage

Au démarrage de l'application ou du worker :

- fichier sans ligne SQLite : quarantaine puis suppression si hors rétention
  technique ;
- ligne `committed` sans fichier : `obsolete` et problème technique ;
- ligne avec SHA-256 différent : `obsolete` et problème technique ;
- ligne `pending` plus ancienne que `SIRCOM_ARTIFACT_PENDING_TTL_SECONDS` :
  `obsolete` ou `quarantined` selon présence du fichier ;
- job `running` ou `leased` avec lease expiré : `expired`, récupérable.

Aucune adoption automatique d'un fichier orphelin comme artefact valide.

## DAG d'invalidation

Dépendances V1 :

- `upload_excel` -> `diagnostic_excel`
- `diagnostic_excel` -> `mapping`
- `mapping` -> `fusion_multi_onglets`
- `fusion_multi_onglets` -> `normalisation_contenu`
- `normalisation_contenu` -> `tri_region_departement`
- `normalisation_contenu` -> `verification_csv_indesign`
- `tri_region_departement` + `verification_csv_indesign` -> `previsualisation_csv`
- `upload_images` -> `inspection_images`
- `inspection_images` + `mapping` -> `matching_images`
- `previsualisation_csv` + `matching_images` -> `rapports`
- `previsualisation_csv` + `matching_images` + `rapports` -> `package_final`
- `package_final` -> `purge_retention`

Chaque fingerprint est le SHA-256 d'un JSON canonique :

- encodage UTF-8 ;
- clés triées ;
- versions de règles incluses ;
- ids et hash des artefacts amont ;
- décisions utilisateur ;
- paramètres de configuration métier utiles ;
- aucune valeur métier sensible.

## Tests obligatoires

- Deux connexions SQLite concurrentes sur acquisition de job.
- Double soumission avec même `idempotency_key`.
- Lease expiré puis reclaim.
- Commit tardif rejeté après nouveau `run_id`.
- Réconciliation d'un fichier sans ligne et d'une ligne sans fichier.
- Invalidation aval après nouvel Excel ou nouveau zip.
- Annulation coopérative pendant job long simulé.
