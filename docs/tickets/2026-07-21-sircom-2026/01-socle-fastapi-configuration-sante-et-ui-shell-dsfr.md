# 01 - Socle FastAPI, configuration, santé et UI shell DSFR

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : une application FastAPI minimale lançable en local, avec
configuration centralisée, routes de santé, OpenAPI disponible, shell UI DSFR
minimal et répertoire `.sircom2026-data/` ignoré par Git.

Critères d'acceptation :

- [ ] Un manifeste de dépendances `pyproject.toml` existe pour FastAPI, tests et
      runtime local.
- [ ] Une commande documentée lance l'application en local sur `127.0.0.1`.
- [ ] Le choix frontend V1 est explicite : templates FastAPI/Jinja et DSFR
      statique, sans SPA sauf décision ultérieure documentée.
- [ ] `GET /health` répond sans dépendre de SQLite, Excel, images ou worker.
- [ ] `GET /health/ready` retourne 200 seulement si la configuration est valide,
      le data dir est créable et inscriptible, une connexion SQLite `SELECT 1`
      réussit même au premier démarrage et l'espace libre est supérieur ou égal
      à `SIRCOM_DISK_FREE_MIN_MB`; sinon 503 avec code stable. Le schéma métier
      reste hors périmètre jusqu'au ticket 03.
- [ ] `GET /api/config/limits` retourne les limites configurées sans exposer de
      chemins disque internes.
- [ ] `/docs` et `/openapi.json` sont disponibles.
- [ ] Un shell HTML minimal affiche le nom de l'application, une navigation de
      base et une zone de contenu sans prétendre à une conformité RGAA.
- [ ] La configuration expose les variables `SIRCOM_DATA_DIR`,
      `SIRCOM_SQLITE_PATH`, `SIRCOM_RETENTION_DAYS`, `SIRCOM_MAX_EXCEL_MB`,
      `SIRCOM_MAX_ZIP_MB`, `SIRCOM_MAX_IMAGE_COUNT`, `SIRCOM_MAX_IMAGE_MB`,
      `SIRCOM_MAX_UNZIPPED_MB`, `SIRCOM_INDESIGN_IMAGE_ROOT`,
      `SIRCOM_BIND_HOST`, `SIRCOM_PORT`, `SIRCOM_WORKER_ENABLED`,
      `SIRCOM_WORKER_ID`, `SIRCOM_MAX_ACTIVE_JOBS` et
      `SIRCOM_DISK_FREE_MIN_MB`.
- [ ] `.sircom2026-data/` est ajouté au `.gitignore`.
- [ ] Tests de configuration pour valeurs par défaut, surcharge par
      environnement et valeur invalide, incluant `SIRCOM_MAX_ACTIVE_JOBS=1` et
      `SIRCOM_DISK_FREE_MIN_MB=5120`.
- [ ] Tests `TestClient` pour `/health`, `/health/ready`,
      `/api/config/limits` et OpenAPI.
- [ ] Tests readiness pour premier démarrage sans SQLite existante, data dir non
      inscriptible, disque juste sous le seuil et disque au seuil.

Hors périmètre :

- création réelle de lots ;
- base SQLite complète ;
- worker ;
- upload de fichiers.

Preuve attendue :

- commande de test ciblée ;
- capture ou sortie montrant les routes de santé.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
