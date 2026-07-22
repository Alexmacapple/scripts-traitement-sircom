# 01 - Socle FastAPI, configuration, santé et UI shell DSFR

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : une application FastAPI minimale lançable en local, avec
configuration centralisée, routes de santé, OpenAPI disponible, shell UI DSFR
minimal et répertoire `.sircom2026-data/` ignoré par Git.

Critères d'acceptation :

- [x] Un manifeste de dépendances `pyproject.toml` existe pour FastAPI, tests et
      runtime local.
- [x] Une commande documentée lance l'application en local sur `127.0.0.1`.
- [x] Le choix frontend V1 est explicite : templates FastAPI/Jinja et DSFR
      statique, sans SPA sauf décision ultérieure documentée.
- [x] `GET /health` répond sans dépendre de SQLite, Excel, images ou worker.
- [x] `GET /health/ready` retourne 200 seulement si la configuration est valide,
      le data dir est créable et inscriptible, une connexion SQLite `SELECT 1`
      réussit même au premier démarrage et l'espace libre est supérieur ou égal
      à `SIRCOM_DISK_FREE_MIN_MB`; sinon 503 avec code stable. Le schéma métier
      reste hors périmètre jusqu'au ticket 03.
- [x] `GET /api/config/limits` retourne les limites configurées sans exposer de
      chemins disque internes.
- [x] `/docs` et `/openapi.json` sont disponibles.
- [x] Un shell HTML minimal affiche le nom de l'application, une navigation de
      base et une zone de contenu sans prétendre à une conformité RGAA.
- [x] La configuration expose les variables `SIRCOM_DATA_DIR`,
      `SIRCOM_SQLITE_PATH`, `SIRCOM_RETENTION_DAYS`, `SIRCOM_MAX_EXCEL_MB`,
      `SIRCOM_MAX_ZIP_MB`, `SIRCOM_MAX_IMAGE_COUNT`, `SIRCOM_MAX_IMAGE_MB`,
      `SIRCOM_MAX_UNZIPPED_MB`, `SIRCOM_INDESIGN_IMAGE_ROOT`,
      `SIRCOM_BIND_HOST`, `SIRCOM_PORT`, `SIRCOM_WORKER_ENABLED`,
      `SIRCOM_WORKER_ID`, `SIRCOM_MAX_ACTIVE_JOBS` et
      `SIRCOM_DISK_FREE_MIN_MB`.
- [x] `.sircom2026-data/` est ajouté au `.gitignore`.
- [x] Tests de configuration pour valeurs par défaut, surcharge par
      environnement et valeur invalide, incluant `SIRCOM_MAX_ACTIVE_JOBS=1` et
      `SIRCOM_DISK_FREE_MIN_MB=5120`.
- [x] Tests `TestClient` pour `/health`, `/health/ready`,
      `/api/config/limits` et OpenAPI.
- [x] Tests readiness pour premier démarrage sans SQLite existante, data dir non
      inscriptible, disque juste sous le seuil et disque au seuil.

Hors périmètre :

- création réelle de lots ;
- base SQLite complète ;
- worker ;
- upload de fichiers.

Preuve attendue :

- commande de test ciblée ;
- capture ou sortie montrant les routes de santé.

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z05-002`.

Titre ShipGuard : la dépendance de test déclare `httpx2` au lieu de `httpx`.

Décision appliquée : l'extra `test` de `pyproject.toml` déclare désormais
`httpx>=0.27,<1`. C'est la dépendance réellement utilisée par
`fastapi.testclient.TestClient`, alors que `httpx2` ne couvre pas ce besoin sur
une installation propre.

Preuve locale :

- parsing `pyproject.toml` : `httpx>=0.27,<1` présent, `httpx2` absent ;
- import environnement courant : `httpx 0.28.1` et `TestClient` importables ;
- suite API/web utilisant `TestClient` :
  `tests.test_web_socle tests.test_lots_api tests.test_api_access_errors`,
  `42 tests`, `OK`.

Limite : je n'ai pas relancé une installation réseau propre de `.[test]` ; la
preuve locale vérifie le manifeste corrigé et l'environnement déjà installé.

## Complément rapport ShipGuard - 2026-07-22 - dépendances 2025

Finding traité : `SG-001`, origine stable `r1-z05-003`.

Titre ShipGuard : dépendances non épinglées par le script maître à
l'exécution.

Décision appliquée : le script maître 2025 ne pose plus `openpyxl`,
`pandas` et `Pillow` comme noms nus. Les dépendances du flux historique sont
centralisées dans `requirements-2025.txt`, avec bornes basses et hautes, puis
installées par `pip install -r requirements-2025.txt`.

Preuve locale :

- `tests.test_sircom_master_dependencies`, `1 test`, `OK` ;
- inspection du manifeste 2025 : `openpyxl>=3.1,<4`, `pandas>=2.2,<3` et
  `Pillow>=12,<13` présents.

Limite : je n'ai pas lancé d'installation réseau propre du flux 2025 ; la
preuve vérifie le chemin d'installation appelé par le script maître et le
contenu versionné des contraintes.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
