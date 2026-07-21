# Design d'architecture web Sircom 2026

Date : 2026-07-21

## Sources

- `AGENTS.md`
- `README.md`
- `TODO.md`
- `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `docs/specs/2026-07-21-orchestration-sircom-2026.md`
- `docs/specs/2026-07-21-contrats-implementation-sircom-2026.md`
- `docs/specs/2026-07-21-design-ui-dsfr-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-execution-stockage-worker-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-exploitation-purge-sircom-2026.md`
- `sircom2026/excel_diagnostic.py`
- `sircom2026/synthetic_excels.py`
- `tests/test_excel_diagnostic.py`

## Verdict

Le prochain incrément doit être une application web FastAPI locale, avec une
API explicite, une interface web légère et un worker local intégré piloté par
SQLite.

Ce document ne décrit pas un service déjà existant : aucun squelette FastAPI
n'est présent dans le dépôt au moment de la rédaction. Il définit l'architecture
cible V1 à implémenter, les frontières de modules, les routes attendues, les
contrats d'artefacts et les preuves minimales à produire.

Les contrats complémentaires d'implémentation ferment les décisions détaillées
post-revues GLM/SOL/Codex. En cas de tension avec une question ouverte
historique de ce document, ils priment pour les tickets V1.

Le design retenu est volontairement conservateur :

- FastAPI sert l'interface et l'API.
- Les routes orchestrent uniquement HTTP, validation et appels de services.
- SQLite persiste lots, étapes, jobs, artefacts, événements et problèmes.
- Les traitements lourds passent par un worker local intégré.
- Les fichiers générés sont stockés hors Git dans un répertoire de données
  configurable.
- Les règles métier 2026 restent indépendantes des positions Excel 2025.

## Famille d'application

Famille : application web métier locale avec API interne.

Mode V1 :

- exécution sur Mac en local ;
- accès par navigateur ;
- un seul processus applicatif principal ;
- un worker local dans le même environnement ;
- stockage SQLite et disque local ;
- pas de dépendance Redis, Celery ou service externe en V1.

Mode cible ultérieur :

- déploiement VPS interne ;
- authentification à préciser ;
- même modèle métier ;
- stockage et file à réévaluer si plusieurs instances deviennent nécessaires.

Cette architecture ne doit pas être vendue comme scalable horizontalement. Le
choix SQLite impose un modèle simple : une instance applicative active, un
writer maîtrisé, des jobs sérialisés ou faiblement concurrents.

## Cycle de vie runtime

Routes froides :

- `GET /health` doit répondre sans charger de fichier Excel, d'image ou de lot.
- `GET /health/ready` vérifie la base SQLite, le répertoire de données et
  l'espace disque minimal.
- `GET /health/ready` retourne 200 seulement si la configuration est valide,
  `SIRCOM_DATA_DIR` est créable et inscriptible, une connexion SQLite `SELECT 1`
  réussit sur `SIRCOM_SQLITE_PATH` même au premier démarrage, et l'espace libre
  est supérieur ou égal à `SIRCOM_DISK_FREE_MIN_MB`. Sinon la route retourne
  503 avec un code stable. Le schéma métier complet reste hors périmètre de
  cette readiness jusqu'au ticket 03.
- `/docs` et `/openapi.json` restent disponibles sans job lancé.

Ressources au démarrage :

- configuration validée ;
- création des répertoires nécessaires si absents ;
- migration SQLite locale ou initialisation de schéma ;
- démarrage optionnel du worker selon configuration.

Ressources par requête :

- session SQLite courte ;
- services applicatifs injectés ;
- aucun traitement long dans la requête HTTP.

Ressources par job :

- lease SQLite du job ;
- accès au lot et aux artefacts ;
- progression persistée ;
- annulation coopérative entre sous-étapes ;
- écriture atomique des artefacts.

## Matrice de claims

| Claim | Source | Verdict | Impact |
|---|---|---|---|
| L'application FastAPI n'existe pas encore dans le dépôt. | Recherche locale `main.py`, `app.py`, `pyproject.toml`, `package.json`. | Connu connu | Les routes ci-dessous sont à implémenter et à tester. |
| Le diagnostic Excel 2026 existe déjà comme logique Python locale. | `sircom2026/excel_diagnostic.py` | Connu connu | Le premier ticket doit le brancher sans déplacer la logique dans une route. |
| Les Excels synthétiques existent déjà. | `sircom2026/synthetic_excels.py` et `tests/test_excel_diagnostic.py` | Connu connu | Ils servent de base de non-régression. |
| Le contrat fonctionnel verrouille le CSV InDesign. | Spec fonctionnelle et `AGENTS.md` | Connu connu | Les modules CSV et package doivent être testés au niveau octets. |
| L'orchestration SQLite est validée comme principe. | Spec orchestration | Connu connu | Le design détaille les tables et transitions. |
| L'authentification VPS n'est pas définie. | Questions ouvertes fonctionnelles | Connu inconnu | Prévoir une frontière `security`, mais ne pas inventer un SSO. |
| Le support HEIC réel n'est pas garanti. | Questions ouvertes fonctionnelles | Connu inconnu | Le module images doit isoler les codecs et documenter les erreurs. |
| Le frontend exact n'est pas encore choisi. | Absence de code web | Connu inconnu | Commencer par templates HTML DSFR ou frontend minimal, sans framework lourd imposé. |

## Principes d'architecture

1. Les routes ne contiennent pas de règles métier.
2. Les étapes du pipeline sont appelables par le worker et testables hors HTTP.
3. Le disque est traité comme un store d'artefacts, pas comme une zone libre.
4. SQLite est la source d'état ; les fichiers sont référencés par table
   `artefacts`.
5. Les noms de fichiers ne portent pas de données sensibles.
6. Les erreurs métier sont des `problemes` structurés ; les erreurs techniques
   restent dans les logs et événements techniques.
7. Les validations humaines sont représentées par le statut `action_requise`.
8. Toute relance invalide explicitement les étapes aval.
9. Les IDs Excel et images restent textuels.
10. Aucun code V1 ne doit réintroduire les lettres Excel 2025 comme règles
    métier.

## Modules profonds

### `sircom2026.app`

Responsabilité : composer l'application FastAPI.

Interface :

- `create_app(settings: Settings) -> FastAPI`
- routes de santé ;
- inclusion des routers ;
- lifespan de démarrage et arrêt.

Dépendances :

- `config` ;
- repositories SQLite ;
- services applicatifs.

Tests :

- `TestClient` sur `/health`, `/health/ready`, `/openapi.json`.

### `sircom2026.config`

Responsabilité : lire, valider et exposer la configuration.

Interface :

- `Settings`
- `load_settings()`

Variables minimales :

- `SIRCOM_DATA_DIR`
- `SIRCOM_SQLITE_PATH`
- `SIRCOM_RETENTION_DAYS`
- `SIRCOM_MAX_EXCEL_MB`
- `SIRCOM_MAX_ZIP_MB`
- `SIRCOM_MAX_IMAGE_COUNT`
- `SIRCOM_MAX_IMAGE_MB`
- `SIRCOM_MAX_UNZIPPED_MB`
- `SIRCOM_INDESIGN_IMAGE_ROOT`
- `SIRCOM_BIND_HOST`
- `SIRCOM_PORT`
- `SIRCOM_WORKER_ENABLED`
- `SIRCOM_WORKER_ID`
- `SIRCOM_MAX_ACTIVE_JOBS`
- `SIRCOM_WORKER_POLL_SECONDS`
- `SIRCOM_WORKER_LEASE_TTL_SECONDS`
- `SIRCOM_WORKER_HEARTBEAT_SECONDS`
- `SIRCOM_DISK_FREE_MIN_MB`

Valeurs V1 recommandées :

- data dir : `.sircom2026-data` ;
- SQLite : `${SIRCOM_DATA_DIR}/sircom.sqlite3` ;
- Excel : 50 Mo ;
- zip images : 1 Go ;
- images : 1500 ;
- taille image : 50 Mo ;
- décompressé : 3 Go ;
- rétention : 7 jours ;
- racine InDesign : `/Users/victoria/Documents/export-jpg-resize` ;
- bind HTTP : `127.0.0.1` ;
- port HTTP : `8000` ;
- worker local : activé ;
- worker ID : `local-1` ;
- jobs actifs maximum : `1` ;
- poll worker : `2` secondes ;
- TTL de lease worker : `300` secondes ;
- heartbeat worker : `30` secondes ;
- disque libre minimal : `5120` MiB.

Tests :

- defaults ;
- surcharge par environnement ;
- refus des valeurs invalides.
- readiness au premier démarrage sans fichier SQLite existant ;
- readiness avec data dir non inscriptible ;
- readiness avec disque juste sous le seuil et au seuil.

### `sircom2026.api`

Responsabilité : exposer les contrats HTTP.

Interface :

- routers par domaine ;
- schémas Pydantic dédiés aux entrées/sorties HTTP ;
- conversion des exceptions applicatives en réponses HTTP.

Dépendances :

- services métier ;
- repositories ;
- store d'artefacts.

Ce module ne doit pas importer directement `pandas`, `openpyxl` ou `Pillow`.

### `sircom2026.orchestration`

Responsabilité : piloter le pipeline, les statuts et la file locale.

Interfaces :

- `PipelineRepository`
- `JobQueue`
- `PipelineRunner`
- `Step`
- `StepContext`

Étapes V1 :

- `upload_excel`
- `diagnostic_excel`
- `mapping`
- `fusion_multi_onglets`
- `normalisation_contenu`
- `previsualisation_csv`
- `upload_images`
- `traitement_images`
- `package_final`

Tests :

- transition nominale ;
- `termine_avec_alertes` ;
- `bloque` versus `echoue` ;
- annulation coopérative ;
- relance depuis l'étape échouée ;
- invalidation aval.

### `sircom2026.artifacts`

Responsabilité : stocker, lire et publier les artefacts de lot.

Interface :

- `ArtifactStore.put_temp_then_commit(...)`
- `ArtifactStore.open_for_read(artifact_id)`
- `ArtifactStore.delete_lot_artifacts(lot_id)`
- `ArtifactManifest`

Contraintes :

- écriture temporaire puis renommage atomique ;
- empreinte SHA-256 ;
- taille persistée ;
- chemin relatif en base ;
- aucun chemin absolu exposé au client ;
- suppression immédiate possible par lot.

### `sircom2026.excel`

Responsabilité : diagnostiquer et lire les classeurs Excel.

Interface initiale :

- conserver ou adapter `sircom2026.excel_diagnostic`.

Évolutions attendues :

- service `ExcelDiagnosticService` ;
- lecture des feuilles utiles ;
- fingerprint structurel ;
- extraction des métadonnées nécessaires au mapping.

Refus stricts V1 :

- cellules fusionnées ;
- en-têtes multi-lignes ;
- colonnes masquées ;
- lignes masquées ;
- onglets masqués ;
- formules ;
- colonnes avec données sans en-tête ;
- impossibilité d'identifier `id_dossier` ;
- doublons `id_dossier` dans un onglet ;
- collisions de noms CSV après nettoyage.

Alertes non bloquantes :

- doublons de noms de colonnes source, si la provenance complète permet de
  continuer ;
- tri région/département non détecté ;
- valeurs date invalides ;
- lignes sans `id_dossier`, supprimées et comptées.

### `sircom2026.mapping`

Responsabilité : produire, valider et persister le mapping.

Interface :

- `build_default_mapping(diagnostic) -> MappingDraft`
- `validate_mapping(mapping, diagnostic) -> MappingValidation`
- `save_mapping_profile(profile)`
- `load_compatible_profile(fingerprint)`

Règles :

- sans profil réutilisable, sélectionner toutes les colonnes utiles par défaut ;
- validation humaine obligatoire ;
- provenance complète pour chaque colonne ;
- un seul `id_dossier` exporté ;
- noms CSV normalisés selon la règle 2025 ;
- `imageid` et `@pathimg` immédiatement après `id_dossier`.

### `sircom2026.transform`

Responsabilité : fusionner et normaliser les données.

Interfaces :

- `FlatMergeService`
- `ContentNormalizer`
- `SortPlanner`

Règles :

- union des `id_dossier` non vides ;
- fusion à plat par clé logique ;
- suppression des lignes sans `id_dossier` ;
- suppression des colonnes entièrement vides ;
- conversion des retours ligne en `<br>` ;
- trim et réduction des espaces ;
- dates au format `dd/mm/yyyy` si colonne date détectée ou confirmée ;
- champs sensibles préservés en texte.

### `sircom2026.exports`

Responsabilité : produire le CSV InDesign et les aperçus.

Interfaces :

- `CsvPreviewService`
- `IndesignCsvWriter`
- `CsvContractVerifier`

Contrat CSV :

- UTF-16 avec BOM ;
- séparateur virgule ;
- fins de ligne LF ;
- guillemets automatiques si nécessaire ;
- cellules vides conservées ;
- en-têtes uniques ;
- `id_dossier`, `imageid`, `@pathimg` en tête logique ;
- aucune valeur `#N/A` injectée ;
- format compatible avec le CSV 2025 de référence.

Tests :

- vérification octet par octet de l'encodage ;
- roundtrip de lecture ;
- comparaison structurelle avec le CSV 2025 de référence ;
- cas cellules vides et guillemets.

### `sircom2026.images`

Responsabilité : traiter le zip images et produire les JPG finaux.

Interfaces :

- `ImageZipInspector`
- `ImageMatcher`
- `ImageProcessor`
- `ImageProblemResolver`

Règles :

- zip source uploadé par lot ;
- images attendues à la racine du zip en V1 ;
- toute image placée dans un sous-dossier du zip est refusée en V1 ; seuls les
  fichiers système explicitement ignorables (`__MACOSX/`, `.DS_Store`) peuvent
  être écartés sans bloquer ;
- une image principale par dossier ;
- absence d'image non bloquante ;
- images non référencées ignorées mais listées ;
- ambiguïtés à résoudre manuellement ;
- JPG final ;
- largeur max 350 px ;
- qualité JPEG 100 ;
- DPI 300 ;
- fond blanc pour transparence ;
- orientation EXIF appliquée ;
- dossier final `export-jpg-resize/`.

### `sircom2026.package`

Responsabilité : assembler le zip final.

Interface :

- `PackageBuilder`
- `PackageVerifier`

Contenu minimal :

- CSV final compatible InDesign ;
- dossier `export-jpg-resize/` ;
- rapport métier ;
- rapport technique ;
- mapping utilisé avec provenance complète ;
- manifeste d'artefacts.

Le package final est produit uniquement après validation humaine.

### `sircom2026.reports`

Responsabilité : produire les rapports métier et technique.

Sections métier minimales :

- résumé du lot ;
- entrées reçues ;
- décisions utilisateur ;
- diagnostic Excel ;
- mapping appliqué ;
- lignes et colonnes supprimées ;
- alertes CSV ;
- bilan images ;
- problèmes par niveau ;
- contenu du package.

Le rapport technique peut contenir codes erreur, durées, tailles, compteurs et
traces anonymisées. Il ne doit pas recopier de valeurs métier sensibles.

## Arborescence cible

Proposition de structure :

```text
sircom2026/
  app/
    main.py
    config.py
    dependencies.py
  api/
    routes/
      health.py
      lots.py
      excel.py
      mapping.py
      csv.py
      images.py
      package.py
      storage.py
    schemas/
      lots.py
      problems.py
      mapping.py
      jobs.py
      artifacts.py
  orchestration/
    models.py
    repository.py
    queue.py
    runner.py
    steps.py
  artifacts/
    store.py
    manifest.py
  excel/
    diagnostic.py
    reader.py
  mapping/
    model.py
    builder.py
    validator.py
    profiles.py
  transform/
    merge.py
    normalize.py
    sort.py
  exports/
    csv_writer.py
    preview.py
    verifier.py
  images/
    zip_inspector.py
    matcher.py
    processor.py
  package/
    builder.py
    verifier.py
  reports/
    business.py
    technical.py
  security/
    uploads.py
```

Le module actuel `sircom2026/excel_diagnostic.py` peut rester en place au
premier ticket. Le déplacement vers `sircom2026/excel/diagnostic.py` n'est utile
que si le coût de migration reste faible et que les imports/tests sont mis à
jour dans le même changement.

## Modèle SQLite

### `lots`

Champs :

- `id`
- `nom`
- `statut`
- `created_at`
- `updated_at`
- `expires_at`
- `deleted_at`
- `final_status`
- `current_step`
- `input_fingerprint`
- `bytes_uploaded`
- `bytes_artifacts`
- `cancel_requested_at`
- `purge_requested_at`

Rôle : source de vérité du lot et de son état global.

### `etapes`

Champs :

- `id`
- `lot_id`
- `step_key`
- `statut`
- `started_at`
- `finished_at`
- `invalidated_at`
- `input_fingerprint`
- `output_fingerprint`
- `progress_current`
- `progress_total`
- `summary_json`

Rôle : état métier détaillé par étape.

### `jobs`

Champs :

- `id`
- `lot_id`
- `step_key`
- `status`
- `priority`
- `attempt`
- `max_attempts`
- `lease_owner`
- `lease_until`
- `cancel_requested_at`
- `created_at`
- `started_at`
- `finished_at`
- `error_code`
- `error_message`

Rôle : file locale persistée pour le worker.

### `artefacts`

Champs :

- `id`
- `lot_id`
- `step_key`
- `kind`
- `role`
- `relative_path`
- `sha256`
- `size_bytes`
- `mime_type`
- `created_at`
- `deleted_at`
- `metadata_json`

Rôle : registre des fichiers produits ou importés.

### `evenements`

Champs :

- `id`
- `lot_id`
- `step_key`
- `level`
- `event_type`
- `message`
- `created_at`
- `technical_json`

Rôle : historique lisible et journal technique anonymisé.

### `problemes`

Champs :

- `id`
- `lot_id`
- `step_key`
- `severity`
- `code`
- `title`
- `cause`
- `location_json`
- `action`
- `details_json`
- `status`
- `created_at`
- `resolved_at`

Niveaux :

- `bloquant`
- `alerte`
- `information`

Rôle : messages structurés affichables dans l'interface et réutilisables dans le
rapport.

## Contrat artefacts disque

Répertoire racine : `SIRCOM_DATA_DIR`, par défaut `.sircom2026-data`.

Structure :

```text
.sircom2026-data/
  sircom.sqlite3
  lots/
    <lot_id>/
      uploads/
      work/
      artifacts/
      package/
      tmp/
```

Règles :

- le répertoire est ignoré par Git ;
- les écritures se font dans `tmp/`, puis commit atomique ;
- les téléchargements passent par `artifact_id`, jamais par chemin fourni par
  l'utilisateur ;
- la purge supprime uploads, artefacts, rapports, packages et valeurs métier ;
- une trace technique anonymisée peut rester selon la politique validée ;
- les compteurs disque sont recalculables depuis SQLite et le disque.

## Matrice des routes

Statut global : à implémenter et à tester.

| Méthode | Route | Entrée | Sortie | Erreurs attendues | Preuve minimale |
|---|---|---|---|---|---|
| GET | `/health` | aucune | process vivant | 500 si erreur inattendue | `TestClient` |
| GET | `/health/ready` | aucune | SQLite, data dir, disque | 503 si non prêt | test avec data dir temporaire |
| GET | `/api/config/limits` | aucune | limites configurées | 500 config invalide | test settings |
| POST | `/api/lots` | nom optionnel | lot créé | 400 entrée invalide | lot en base |
| GET | `/api/lots` | filtres simples | liste paginée | 400 filtre invalide | pagination |
| GET | `/api/lots/{lot_id}` | lot_id | détail lot | 404 inconnu | état + étapes |
| DELETE | `/api/lots/{lot_id}` | lot_id | suppression logique demandée | 404 ; 202 si annulation coopérative requise | tombstone persisté |
| POST | `/api/lots/{lot_id}/excel` | fichier Excel | artefact upload + job diagnostic | 413, 415, 422 | upload borné |
| GET | `/api/lots/{lot_id}/excel/diagnostic` | lot_id | diagnostic structuré | 404, 409 non prêt | problèmes affichables |
| PUT | `/api/lots/{lot_id}/mapping` | mapping draft | mapping sauvegardé | 422 mapping invalide | provenance complète |
| POST | `/api/lots/{lot_id}/mapping/validate` | décision | étape validée/job fusion | 409 mauvais état | action requise levée |
| POST | `/api/lots/{lot_id}/sort/validate` | choix tri | décision persistée | 409 mauvais état | tri ou ordre Excel |
| POST | `/api/lots/{lot_id}/csv/preview` | lot_id | job aperçu CSV | 409 prérequis manquant | artefact preview |
| POST | `/api/lots/{lot_id}/csv/validate` | décision | validation CSV | 409 mauvais état | étape validée |
| POST | `/api/lots/{lot_id}/images` | zip images | artefact upload + job images | 413, 415, 422 | zip sécurisé |
| GET | `/api/lots/{lot_id}/images/status` | lot_id | bilan images | 404 | problèmes images |
| POST | `/api/lots/{lot_id}/images/problems/{problem_id}/resolve` | résolution | problème résolu | 404, 409, 422 | résolution persistée |
| POST | `/api/lots/{lot_id}/package` | décision | job package | 409 prérequis manquant | package artifact |
| GET | `/api/lots/{lot_id}/downloads/{artifact_id}` | ids | flux fichier | 404 absent, supprimé, obsolète ou mauvais lot | chemin non exposé |
| POST | `/api/lots/{lot_id}/retry` | étape | job relancé | 409 état incompatible | invalidation aval |
| POST | `/api/lots/{lot_id}/cancel` | lot_id | annulation demandée | 404 | cancel flag |
| GET | `/api/storage` | aucune | usage global + lots | 500 | indicateurs disque |

Les routes de téléchargement doivent vérifier que l'artefact appartient au lot.
La réponse publique reste indiscernable : 404 pour artefact absent, supprimé,
obsolète ou appartenant à un autre lot ; le motif réel reste seulement dans un
événement technique anonymisé.
Les routes de mutation doivent contrôler le statut courant avant d'accepter une
transition.

## Flux nominal

1. L'utilisateur crée un lot.
2. Il charge l'Excel.
3. L'application enregistre l'upload, lance `diagnostic_excel` et affiche les
   problèmes.
4. Si le diagnostic est bloquant, le lot passe en `bloque`.
5. Si le diagnostic est acceptable, l'application propose un mapping par défaut
   ou un profil compatible.
6. L'utilisateur valide le mapping.
7. Le worker fusionne les onglets utiles et normalise le contenu.
8. L'utilisateur valide le tri proposé ou confirme la conservation de l'ordre
   Excel.
9. Le worker produit un aperçu CSV.
10. L'utilisateur valide l'aperçu CSV.
11. L'utilisateur charge le zip images.
12. Le worker traite les images et signale absences, images ignorées et
    ambiguïtés.
13. L'utilisateur résout les ambiguïtés bloquantes ou continue avec alertes.
14. L'utilisateur confirme la génération du package final.
15. Le worker produit le package et le rapport.
16. L'utilisateur télécharge le package.

## Transitions clés

`termine_avec_alertes` signifie que l'étape est exploitable et que le pipeline
peut continuer jusqu'au prochain point de validation humaine.

`action_requise` signifie qu'une validation ou résolution humaine est attendue.

`bloque` signifie qu'une correction utilisateur est attendue, par exemple un
Excel sale refusé ou une ambiguïté d'image non résolue.

`echoue` signifie erreur technique ou inattendue, par exemple exception non
prévue, écriture disque impossible ou artefact corrompu.

`annule` est porté au niveau lot/job et à l'étape en cours. Le worker termine la
sous-opération courante avant de marquer l'annulation.

## Invalidation aval

Toute modification d'un input ou d'une décision invalide les étapes dépendantes.

Exemples :

- nouvel Excel : invalide diagnostic, mapping, fusion, normalisation, preview,
  images si le matching dépendait de données, package ;
- changement mapping : invalide fusion, normalisation, preview, package ;
- changement tri : invalide preview et package ;
- nouveau zip images : invalide traitement images et package ;
- résolution d'ambiguïté image : invalide traitement images ou package selon
  le moment.

Chaque invalidation doit écrire un événement technique et mettre les artefacts
aval en obsolètes sans les supprimer immédiatement, sauf purge explicite.

## Export testable

Un lot est exportable seulement si les conditions suivantes sont vraies :

- l'Excel accepté possède au moins un onglet utile ;
- chaque onglet utile a une colonne logique `id_dossier` ;
- le mapping est validé ;
- une seule colonne `id_dossier` est exportée ;
- `imageid` et `@pathimg` sont placés juste après `id_dossier` ;
- les lignes sans `id_dossier` ont été supprimées et comptées ;
- les colonnes entièrement vides ont été supprimées et comptées ;
- le tri est validé ou l'ordre Excel conservé est explicitement confirmé ;
- l'aperçu CSV correspond aux fingerprints courants ;
- le CSV final vérifie encodage, séparateur, LF et en-têtes ;
- le traitement images est terminé, terminé avec alertes ou explicitement
  ignoré par décision utilisateur ;
- les problèmes bloquants sont résolus ;
- le rapport métier existe ;
- le manifeste du package référence tous les artefacts attendus.

## Profils de mapping

Un profil de mapping contient :

- nom du profil ;
- version du format ;
- fingerprint structurel Excel ;
- feuilles sources ;
- lettre de colonne ;
- nom original ;
- type logique si confirmé ;
- nom CSV final ;
- statut exporté ou supprimé ;
- position de sortie ;
- date de création ;
- date de dernière utilisation.

Compatibilité :

- même ensemble d'onglets utiles ou stratégie de correspondance explicite ;
- mêmes en-têtes originaux sur les colonnes mappées ;
- même détection `id_dossier` ;
- absence de collision après nettoyage.

Même si un profil est compatible, la validation humaine reste obligatoire en V1.

## Messages d'erreur

Chaque problème affichable doit suivre cette structure :

- niveau ;
- titre court ;
- cause probable ;
- emplacement ;
- action attendue ;
- détails techniques dépliables ;
- code stable.

Exemple pour Excel sale :

```text
Titre : Colonnes masquées détectées
Niveau : bloquant
Cause : le fichier Excel contient des colonnes masquées dans un onglet utile.
Action : afficher toutes les colonnes dans Excel, enregistrer le fichier, puis le recharger.
Détails : onglet, lettres de colonnes, règle de refus.
Code : EXCEL_HIDDEN_COLUMNS
```

Les détails techniques ne doivent pas recopier les valeurs métier des cellules.

## Sécurité uploads

Contrôles Excel :

- extension autorisée ;
- taille maximale ;
- fichier lisible par `openpyxl` ;
- refus si archive invalide ou corrompue ;
- stockage sous nom interne.

Contrôles zip :

- extension et signature ;
- taille compressée ;
- taille décompressée ;
- nombre de fichiers ;
- taille par image ;
- refus des chemins absolus ;
- refus des chemins avec `..` ;
- refus des noms de fichiers vides ou de contrôle ;
- extraction dans un répertoire temporaire du lot ;
- nettoyage en cas d'échec.

Le zip uploadé est la source images du lot. Il ne doit jamais être confondu avec
le chemin final InDesign.

## UI cible

Écrans V1 :

- liste des lots ;
- détail lot avec indicateur global ;
- timeline des étapes ;
- panneau problèmes par niveau ;
- upload Excel ;
- diagnostic Excel ;
- mapping ;
- validation tri ;
- aperçu CSV ;
- upload et traitement images ;
- résolution des ambiguïtés images ;
- package final ;
- stockage et purge.

L'interface doit afficher :

- statut global du lot ;
- statut par étape ;
- progression des jobs ;
- problèmes structurés ;
- détails techniques dépliables ;
- actions disponibles selon statut ;
- usage disque global et par lot.

Le DSFR est une cible de cohérence visuelle. Aucune conformité RGAA ne doit être
revendiquée tant qu'un audit dédié n'a pas été réalisé.

## Déploiement

Commande cible locale :

```bash
uvicorn sircom2026.app.main:app --host 127.0.0.1 --port 8000
```

Contraintes locales :

- bind par défaut sur `127.0.0.1` ;
- pas d'auth obligatoire en local V1 ;
- stockage dans `SIRCOM_DATA_DIR` ;
- un worker local ;
- logs techniques anonymisés.

Contraintes VPS futures :

- authentification à préciser ;
- HTTPS ou terminaison TLS par proxy ;
- protection des routes de téléchargement ;
- répertoire de données persistant ;
- politique de sauvegarde et purge ;
- surveillance disque.

## Raccourcis interdits

- Lancer conversion images, zip ou package dans une requête HTTP bloquante.
- Utiliser `BackgroundTasks` FastAPI pour les traitements lourds critiques.
- Coder en dur `B_ID`, `F_ID` ou une position Excel comme règle 2026.
- Lire des images depuis un ancien dossier local au lieu du zip uploadé.
- Écrire des artefacts hors `SIRCOM_DATA_DIR`.
- Exposer des chemins disque absolus en réponse API.
- Mettre des valeurs métier sensibles dans les logs.
- Injecter `#N/A` dans le CSV final.
- Produire un package si des problèmes bloquants restent ouverts.
- Marquer une étape `termine` quand elle contient encore des alertes.
- Créer des routes stub qui retournent succès sans artefact vérifiable.

## Preuves minimales par ticket

Pour le squelette FastAPI :

- `/health` répond ;
- `/health/ready` couvre SQLite, data dir et disque ;
- OpenAPI généré ;
- configuration testée.

Pour l'upload Excel :

- fichier trop gros refusé ;
- extension invalide refusée ;
- Excel valide accepté ;
- diagnostic existant appelé hors route ;
- problèmes structurés persistés.

Pour l'orchestration :

- création lot ;
- création étapes ;
- job pris par worker ;
- progression persistée ;
- annulation coopérative ;
- retry avec invalidation aval.

Pour le CSV :

- encodage UTF-16 avec BOM prouvé ;
- LF prouvé ;
- ordre des colonnes prouvé ;
- comparaison structurelle avec référence 2025 ;
- cellules vides conservées.

Pour les images :

- zip traversal refusé ;
- zip trop gros refusé ;
- image absente non bloquante ;
- image non référencée listée ;
- ambiguïté résoluble ;
- JPG final vérifié.

Pour le package :

- zip contient les fichiers minimaux ;
- manifeste cohérent ;
- chemins `@pathimg` conformes ;
- rapport métier généré ;
- téléchargement par `artifact_id`.

## Passe critique avocat du diable

### Cible relue

La cible de cette revue est le présent document d'architecture. L'artefact
adjacent le plus risqué reste la future découpe en tickets : si les tickets
perdent les garde-fous de cette spec, l'implémentation peut redevenir un simple
empilement de routes.

### Steel-man

Cette architecture fait le bon choix de séparation : HTTP, pipeline, artefacts,
Excel, mapping, CSV, images et rapports ont des frontières distinctes. Elle
évite deux pièges fréquents : mettre les traitements longs dans les routes et
reprendre les scripts 2025 comme architecture web.

Le choix SQLite + worker local est cohérent avec la V1 locale : moins de
dépendances, tests reproductibles, état inspectable et coûts d'exploitation
faibles. Les limites de ce choix sont nommées au lieu d'être masquées.

### Préoccupations classées

1. Cohérence SQLite/disque insuffisamment contractualisée.
   Sévérité : Haute. Statut : bloquante avant le ticket worker/store.
   Cadre : pré-mortem et modes de défaillance.
   Description : si un job écrit un fichier puis échoue avant l'enregistrement
   en base, ou enregistre l'artefact puis échoue avant le renommage final, le lot
   peut devenir incohérent.
   Conséquence : relance, purge, téléchargement ou package peuvent manipuler des
   artefacts obsolètes, absents ou doublonnés.
   Recommandation : faire du `ArtifactStore` un des premiers tickets, avec
   écriture temporaire, commit atomique, états `pending/committed/obsolete`, test
   de crash simulé et réparation au démarrage.

2. Idempotence et concurrence du worker encore trop implicites.
   Sévérité : Haute. Statut : bloquante avant le ticket orchestration.
   Cadre : inversion et concurrence.
   Description : la spec dit worker local et leases, mais ne fixe pas encore les
   contraintes uniques, le comportement double-clic, ni la règle "un job actif
   par lot/étape".
   Conséquence : double diagnostic, double package, invalidation aval perdue ou
   étape marquée terminée par un ancien job.
   Recommandation : imposer des contraintes SQLite uniques, une clé
   d'idempotence par action utilisateur, un `run_id` par étape et des tests de
   double soumission.

3. Authentification future trop loin du design des routes.
   Sévérité : Haute. Statut : bloquante avant VPS, à surveiller en local.
   Cadre : sécurité et questionnement socratique.
   Description : le local sans auth est acceptable, mais les routes de lot et de
   téléchargement prennent des IDs manipulables. Si la frontière sécurité arrive
   trop tard, l'autorisation sera collée après coup.
   Conséquence : risque d'accès croisé à un lot ou à un artefact dès qu'il y a
   plusieurs utilisateurs ou un proxy exposé.
   Recommandation : introduire dès le squelette une interface
   `AccessPolicy/ActorContext`, implémentée en `permit_local` pour V1, avec tests
   `artifact_id` hors lot et refus par politique.

4. L'oracle CSV 2025 est nommé, mais pas encore transformé en contrat exécutable.
   Sévérité : Haute. Statut : bloquante avant export CSV.
   Cadre : chapeau blanc et preuves.
   Description : "compatible InDesign 2025" peut être interprété différemment
   par deux agents : encodage, BOM, LF, ordre, guillemets, cellules vides et noms
   de colonnes doivent être vérifiés par code.
   Conséquence : un CSV visuellement correct peut casser InDesign ou diverger du
   fichier de référence.
   Recommandation : créer un vérificateur de contrat CSV avant le writer final,
   avec assertions octets, fixture synthétique et comparaison structurelle avec
   `9-final-sircom-indesign-utf16.csv`.

5. La frontière frontend reste trop large pour un ticket prêt à coder.
   Sévérité : Moyenne. Statut : à surveiller.
   Cadre : clarification et chapeau bleu.
   Description : la spec accepte "interface web légère" et DSFR sans choisir
   serveur-rendered, HTMX, React/Vite ou autre approche.
   Conséquence : le premier ticket UI peut partir dans une architecture plus
   lourde que nécessaire ou produire une API sans expérience testable.
   Recommandation : trancher au ticket 1 : templates FastAPI/Jinja + DSFR et
   JavaScript minimal par défaut, sauf décision explicite contraire.

6. Les profils de mapping restent un futur piège de réutilisation silencieuse.
   Sévérité : Moyenne. Statut : à surveiller.
   Cadre : questionnement socratique et cas limites.
   Description : le fingerprint structurel est prévu, mais pas les cas de
   compatibilité partielle, onglet renommé, colonne déplacée ou collision apparue
   après nettoyage.
   Conséquence : un profil peut sembler compatible et exporter la mauvaise
   colonne sous un nom valide.
   Recommandation : V1 sans application automatique silencieuse : profil chargé
   seulement en brouillon, différences affichées, validation humaine obligatoire
   et test de non-régression sur collision.

7. Les écarts Mac/VPS pour images et disque sont sous-estimés.
   Sévérité : Moyenne. Statut : à surveiller.
   Cadre : environnement et cas limites.
   Description : Pillow, HEIC, profils ICC, volumes zip et chemins InDesign
   dépendent fortement de l'environnement.
   Conséquence : le flux peut marcher sur le Mac local puis échouer en VPS ou
   produire des images différentes.
   Recommandation : ajouter un ticket spike image/environnement avant package
   final : versions dépendances, support HEIC décidé, fixture EXIF/transparence,
   smoke test disque bas.

### Verdict avocat du diable

Verdict : Livrer avec modifications.

L'architecture de base tient. Elle ne doit pas être repensée, mais les points
1 à 4 doivent devenir des critères d'acceptation explicites avant les tickets
worker, sécurité VPS et export CSV. Sans cela, le risque n'est pas un mauvais
choix de stack ; c'est une implémentation qui paraît propre en démo mais perd la
cohérence des lots, des artefacts ou du CSV.

## Analyse connu-inconnu

Reformulation : le projet vise une V1 web locale Sircom 2026 qui transforme un
Excel multi-onglets et un zip images en package InDesign traçable. Le design est
assez cadré pour lancer l'implémentation, mais plusieurs décisions doivent être
verrouillées avant les tickets qui touchent stockage, sécurité, export et UI.

### Connus connus

- `[!]` Le CSV final doit rester strictement compatible InDesign 2025 : UTF-16
  avec BOM, virgule, LF, cellules vides conservées, `id_dossier`, `imageid`,
  `@pathimg`.
- `[^]` FastAPI est la cible web et les routes doivent rester minces.
- `[^]` SQLite local est la source de vérité V1 pour lots, étapes, jobs,
  artefacts, événements et problèmes.
- `[^]` Le worker local intégré est requis pour les traitements longs.
- `[^]` Le diagnostic Excel V1 existe déjà en code et doit être branché hors
  route HTTP.
- `[^]` Les données réelles, uploads, artefacts, logs, sauvegardes et images ne
  doivent pas être commitées.
- `[~]` Les statuts métier français et identifiants internes sans accents sont
  connus.

### Connus inconnus

- `[!]` Authentification et autorisation VPS : décider acteur, session,
  protection des téléchargements et politique d'accès par lot.
- `[^]` Contrat exact d'idempotence worker : décider contraintes uniques,
  `run_id`, double soumission et récupération après crash.
- `[^]` Contrat exécutable CSV : décider fixtures, golden files, seuil de
  comparaison et messages d'échec.
- `[^]` Frontend V1 : décider templates FastAPI/Jinja + DSFR ou autre stack.
- `[^]` Format final des profils de mapping : décider fingerprint,
  compatibilité partielle et comportement en cas d'écart.
- `[~]` Politique zip avec sous-dossiers : résolue en V1. Toute image dans un
  sous-dossier est refusée ; seuls `__MACOSX/` et `.DS_Store` peuvent être
  ignorés sans bloquer.
- `[~]` Support HEIC réel : décider si V1 supporte, refuse clairement ou dépend
  d'une option d'installation.
- `[~]` Sauvegarde du répertoire de données : décider hors V1, manuel ou
  mécanisme documenté.

### Inconnus connus

- `[^]` "Local mono-utilisateur" masque probablement un futur usage
  multi-utilisateur dès le passage VPS.
- `[^]` "SQLite suffit" masque une obligation de discipline sur transactions,
  contraintes et verrous applicatifs.
- `[^]` "Compatible CSV 2025" masque des détails invisibles à l'oeil nu mais
  décisifs pour InDesign.
- `[~]` "Les utilisateurs corrigeront l'Excel" masque le besoin de messages
  d'erreur très précis, sinon ils rechargeront plusieurs fois le même fichier.
- `[~]` "Zip images à la racine" masque les habitudes réelles de zip générés par
  macOS ou Windows, souvent avec dossiers, fichiers cachés ou doublons.
- `[~]` "DSFR" masque le fait que cohérence visuelle et conformité RGAA ne sont
  pas équivalentes.
- `[~]` "Rapport technique anonymisé" masque la difficulté de ne jamais recopier
  une valeur métier dans une exception, un nom de fichier ou un JSON de détail.

### Inconnus inconnus

- `[^]` Changement futur du format Démarches Simplifiées qui casse les
  hypothèses d'onglets, d'en-têtes ou d'identifiants.
- `[^]` Comportement InDesign non documenté sur certains caractères, retours
  ligne, champs vides ou noms de colonnes courts.
- `[^]` Contraintes sécurité ou hébergement imposées tardivement pour le VPS.
- `[~]` Photos avec profils colorimétriques, rotations ou transparences qui
  passent les tests simples mais produisent un rendu inacceptable.
- `[~]` Lots simultanés plus fréquents que prévu, saturant disque, CPU ou temps
  de traitement.
- `[~]` Besoin d'audit accessibilité après design UI, révélant des contraintes
  qui auraient dû guider les composants plus tôt.

### Risques prioritaires

1. `[!]` Perte de cohérence lot/artefacts en cas d'échec partiel.
2. `[^]` CSV produit mais incompatible InDesign malgré une apparence correcte.
3. `[^]` Autorisation ajoutée trop tard et routes de téléchargement difficiles à
   sécuriser.
4. `[^]` Worker relançable mais non idempotent.
5. `[~]` UI de mapping trop ouverte et source d'exports faux mais valides.

### Questions prioritaires

1. Quelle politique d'accès doit-on simuler dès la V1 locale pour éviter une
   refonte sécurité au VPS ?
2. Quel est le test minimal qui prouve qu'un artefact disque et son entrée
   SQLite sont cohérents après échec simulé ?
3. Quel jeu de fixtures devient l'oracle CSV officiel : référence 2025 seule,
   synthétique dédié, ou les deux ?
4. Résolu V1 : les zip images avec sous-dossiers sont refusés dès qu'une image
   s'y trouve ; `__MACOSX/` et `.DS_Store` seuls peuvent être ignorés.
5. Le frontend V1 part-il sur templates FastAPI/Jinja + DSFR par défaut ?

### Verdict connu-inconnu

Verdict : Prêt sous conditions.

La spec est assez stable pour être découpée en tickets, à condition que les
premiers tickets verrouillent les quatre zones de brouillard critiques :
cohérence artefacts, idempotence worker, sécurité de frontière et oracle CSV.
Ces sujets doivent être des critères d'acceptation, pas des notes de bas de page.

## Tensions à lever pour implémentation LLM

- Architecture cible versus code existant : ne pas prétendre que les routes
  existent déjà.
- Découpe verticale versus grand échafaudage : ne pas créer toute
  l'arborescence cible avec des modules vides ; chaque ticket doit livrer un flux
  vérifiable.
- Arborescence cible versus refactor opportuniste : ne pas déplacer
  `sircom2026/excel_diagnostic.py` sans besoin immédiat, tests migrés et imports
  corrigés.
- SQLite simple versus multi-instance : ne pas préparer une architecture
  distribuée sans besoin V1.
- Worker local versus `BackgroundTasks` : les jobs critiques doivent être
  persistés.
- Idempotence versus simple relance : une relance doit être sûre même après un
  échec au milieu d'une écriture.
- Routes FastAPI versus JSON libre : définir des schémas Pydantic et erreurs
  structurées, ne pas retourner des dictionnaires opportunistes difficiles à
  stabiliser.
- Artefacts disque versus chemins API : ne jamais exposer les chemins internes.
- Référence 2025 versus règle 2026 : utiliser 2025 comme oracle de sortie, pas
  comme mapping codé en dur.
- Chemin InDesign final versus zip source : `SIRCOM_INDESIGN_IMAGE_ROOT` sert à
  écrire `@pathimg`, mais les images sources viennent toujours du zip uploadé.
- Mapping par défaut versus validation humaine : le défaut accélère mais ne
  remplace pas la validation.
- Profil compatible versus profil appliqué : la compatibilité doit produire un
  brouillon, jamais un export silencieux.
- Fixtures synthétiques versus données réelles : les tests doivent éviter les
  données métier réelles et ne jamais commiter uploads, artefacts ou logs.
- Alertes versus blocages : `termine_avec_alertes` continue ; `bloque` attend
  une correction utilisateur ; `echoue` signale une erreur technique.
- Rapport métier versus logs techniques : ne pas mélanger valeurs métier et
  traces d'exécution.
- Local sans auth versus VPS protégé : prévoir l'interface de politique d'accès
  dès le local, même si l'implémentation locale autorise tout.

## Prochaine découpe recommandée

Produire ensuite des tickets unitaires dans cet ordre :

1. Squelette FastAPI, configuration, santé et `.sircom2026-data/` ignoré par
   Git.
2. Schéma SQLite minimal, contraintes d'unicité et repositories
   lots/étapes/jobs.
3. Store d'artefacts disque avec écritures atomiques et test d'échec simulé.
4. Worker local minimal avec lease, `run_id`, idempotence et job diagnostic.
5. Upload Excel + diagnostic persisté.
6. Mapping par défaut, profil en brouillon et validation humaine.
7. Fusion multi-onglets et normalisation.
8. Vérificateur de contrat CSV avant writer final.
9. Aperçu CSV et export UTF-16 prouvé.
10. Upload zip images et inspection sécurisée.
11. Traitement images, spike environnement et résolution des ambiguïtés.
12. Package final et téléchargement par artefact.
13. Purge, rétention, indicateurs disque et trace anonymisée.

Chaque ticket doit livrer une preuve observable et éviter les stubs de succès.
