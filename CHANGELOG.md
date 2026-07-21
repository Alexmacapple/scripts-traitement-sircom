# Changelog

## 2026-07-21

- Implémentation du ticket 01 Sircom 2026 : socle FastAPI local, configuration
  `SIRCOM_*`, routes `/health`, `/health/ready`, `/api/config/limits`, OpenAPI,
  shell Jinja/DSFR minimal et tests ciblés.
- Implémentation du ticket 04 Sircom 2026 : création de lots, étapes V1
  initialisées, consultation paginée, suppression logique, annulation
  coopérative des jobs actifs et timeline UI DSFR.
- Ajout d'une preuve Playwright opt-in pour l'UI lots desktop/mobile : création,
  sélection, timeline visible et suppression logique.
- Implémentation du ticket 05 Sircom 2026 : store d'artefacts atomique,
  téléchargement par `artifact_id`, 404 indiscernable et réconciliation
  disque/SQLite.
- Implémentation du ticket 06 Sircom 2026 : transitions de statuts métier,
  problèmes structurés avec cause/action, événements séparés, compteurs ouverts
  et rendu DSFR minimal des problèmes et événements dans le détail de lot.
- Implémentation du ticket 07 Sircom 2026 : worker local SQLite, acquisition par
  lease, `run_id`, fencing, idempotence de soumission, progression persistée,
  annulation coopérative et runner CLI `scripts-2026/run_worker_once.py`.
- Implémentation du ticket 08 Sircom 2026 : DAG d'invalidation V1 centralisé,
  fingerprints SHA-256 de JSON canonique, relance idempotente d'étape échouée,
  invalidation aval, artefacts/problèmes obsolètes, route
  `POST /api/lots/{lot_id}/retry` et action DSFR minimale de relance.
- Implémentation du ticket 09 Sircom 2026 : route
  `POST /api/lots/{lot_id}/excel`, validation taille/extension/archive,
  stockage de l'Excel source via `ArtifactStore`, invalidation aval,
  planification de `diagnostic_excel` et formulaire DSFR d'upload.
- Implémentation du ticket 10 Sircom 2026 : diagnostic Excel exécuté par le
  worker local, résultat JSON persisté comme artefact, route
  `GET /api/lots/{lot_id}/excel/diagnostic` et problèmes structurés
  bloquants/alertes/informations.
- Ajout des contrats complémentaires d'implémentation Sircom 2026 : index
  normatif, UI DSFR, exécution/stockage/worker, données CSV/images et
  exploitation/purge.
- Fermeture documentaire de la passe de décisions aval : schéma run-scopé,
  `run_id`, `idempotency_key`, `lease_version`, réconciliation d'artefacts,
  DAG/fingerprints, `ImageBindings`, sémantique `imageid` sans image, purge et
  traces anonymisées.
- Mise à jour des tickets unitaires : tous les tickets sont `ready-for-agent`
  côté cadrage, tout en conservant la frontier d'exécution au ticket 01 puis le
  graphe de dépendances.
- Ajout des garde-fous d'implémentation dans `docs/agents/` : prompt verrouillé
  pour le ticket 01, template de review post-ticket et exclusion des sorties
  locales `.claude/outputs/`.
- Ajout des rapports de vérification globale GLM et SOL, puis synthèse
  GLM/SOL/Codex pour arbitrer le lancement de l'implémentation Sircom 2026.
- Application du patch documentaire P0 avant ticket 01 : defaults V1
  `SIRCOM_MAX_ACTIVE_JOBS=1`, `SIRCOM_DISK_FREE_MIN_MB=5120` et contrat précis
  de `/health/ready`.
- Clarification documentaire des exceptions de nommage `id_dossier`,
  `imageid`, `@pathimg`, du refus V1 des images en sous-dossiers de zip et du
  téléchargement 404 indiscernable par `artifact_id`.
- Alignement post-revue SOL : statuts unitaires des tickets aval, route DELETE
  en suppression logique/tombstone, politique zip stricte partout et décision
  dédiée sur la réconciliation du store d'artefacts avant ticket 05.
- Ajout de `sircom2026.excel_diagnostic` et `scripts-2026/diagnose_excel.py` pour diagnostiquer les inputs Excel 2026 sans exposer les données métier.
- Ajout de `sircom2026.synthetic_excels` et `scripts-2026/create_synthetic_excels.py` pour générer des classeurs synthétiques de test.
- Ajout de tests unitaires ciblés pour les cas multi-onglets valides et les refus V1 : ID manquant, ID dupliqué, ID ambigu, cellules fusionnées, colonne masquée, formule et en-tête multi-ligne.
- Analyse structurelle des fichiers retrouvés `Sircom1.xlsx` et `Sircom2.xlsx` : `Sircom1.xlsx` est refusé par les règles V1 à cause de colonnes masquées et formules ; `Sircom2.xlsx` est acceptable avec l'onglet vide `Avis` ignoré.
- Formalisation de la spec locale `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md` pour le contrat fonctionnel Q0-Q79 : interface, import Excel, mapping, fusion multi-onglets, CSV InDesign, images, aperçu, rapport, package et seams de test.
- Formalisation de la spec locale `docs/specs/2026-07-21-orchestration-sircom-2026.md` pour l'orchestration V1 : pipeline typé, SQLite, worker local, statuts français, validations, reprise, annulation, purge et messages Excel sale.
- Formalisation de la spec locale `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md` pour relier contrat fonctionnel et orchestration à une architecture FastAPI/SQLite/worker local testable.
- Renforcement de la spec d'architecture avec une passe connu-inconnu et avocat du diable : sévérités, risques prioritaires, verdicts et critères bloquants avant tickets worker, artefacts, sécurité et CSV.
- Déplacement du journal de cadrage `cuisine-moi` vers `docs/cuisine-moi/` et mise à jour des références Markdown.
- Réécriture de `README.md` sans emojis en guide d'ensemble Sircom 2025/2026 : flux 2025, outils 2026, règles métier verrouillées, artefacts et vérifications.
- Refonte de `TODO.md` en feuille de route structurée : terminé, priorité 0, socle FastAPI, orchestration, import Excel, CSV, images, package, exploitation et recette.
- Publication locale de `docs/tickets/2026-07-21-tickets-implementation-sircom-2026.md` avec 23 tickets `ready-for-agent`, dépendances explicites, frontier initiale et matrice de couverture des specs.
- Renforcement du fichier de tickets avec passes avocat du diable et connu-inconnu, clarification des dépendances upload/invalidation et des critères du socle FastAPI.
- Découpage des tickets Sircom 2026 en fichiers Markdown unitaires dans `docs/tickets/2026-07-21-sircom-2026/`, avec index principal et README de dossier.
- Revue de chaque ticket unitaire avec passe connu-inconnu et avocat du diable,
  puis renforcement ciblé des critères d'acceptation sensibles.
- Passe finale anti-tension LLM sur les tickets : renommage du libellé de
  dépendance en `Dépend de`, fermeture des formulations ambiguës et fixation des
  noms d'artefacts rapport/package V1.

## 2026-07-20

- Clonage et reprise du dépôt de scripts Sircom.
- Archivage des scripts historiques dans `scripts-2025/` et adaptation de l'orchestrateur.
- Ajout de `AGENTS.md` comme source locale de consignes agent.
- Ajout de `TODO.md` pour suivre les tâches de cadrage et d'implémentation.
- Cadrage de l'interface web Sircom 2026 dans `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md`.
- Décision d'architecture cible : FastAPI, Swagger/OpenAPI, frontend DSFR, exécution locale Mac Alex puis VPS interne.
- Décision de traitement 2026 : Excel multi-onglets, fusion à plat par `id_dossier`, mapping semi-automatique avec profils, export CSV final strictement compatible avec le CSV InDesign 2025 de référence.
- Décision images 2026 : zip images en entrée, images à la racine, conversion JPG, dossier final `export-jpg-resize/`, absences non bloquantes avec alertes.
