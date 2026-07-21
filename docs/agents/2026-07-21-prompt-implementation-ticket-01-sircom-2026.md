# Prompt d'implémentation - Ticket 01 Sircom 2026

Date : 2026-07-21

## Prompt à transmettre

Mission : implémenter le ticket 01 de Sircom 2026, et uniquement celui-ci.

Frontier active : `01`.

Ne pas ouvrir ni anticiper les tickets 02 à 23 dans cette session.

### À lire avant de coder

Lis dans cet ordre :

1. `AGENTS.md`
2. `docs/tickets/2026-07-21-tickets-implementation-sircom-2026.md`
3. `docs/tickets/2026-07-21-sircom-2026/01-socle-fastapi-configuration-sante-et-ui-shell-dsfr.md`
4. `docs/specs/2026-07-21-contrats-implementation-sircom-2026.md`
5. `docs/specs/2026-07-21-design-ui-dsfr-sircom-2026.md`
6. `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`

### Périmètre autorisé

Tu dois livrer :

- `pyproject.toml` avec FastAPI, tests et runtime local ;
- une commande documentée pour lancer l'application sur `127.0.0.1` ;
- configuration centralisée exposant les 15 variables V1 du ticket ;
- `GET /health` indépendant de SQLite, Excel, images et worker ;
- `GET /health/ready` avec :
  - configuration valide ;
  - data dir créable et inscriptible ;
  - `SELECT 1` SQLite possible même au premier démarrage ;
  - espace libre supérieur ou égal à `SIRCOM_DISK_FREE_MIN_MB` ;
  - réponse 503 avec code stable si readiness échoue ;
- `GET /api/config/limits` sans chemin disque interne ;
- `/docs` et `/openapi.json` disponibles ;
- shell HTML minimal FastAPI/Jinja + assets DSFR statiques ;
- `.sircom2026-data/` ajouté au `.gitignore` ;
- tests config et `TestClient` demandés par le ticket.

### Hors périmètre strict

Ne pas coder :

- création ou consultation de lots ;
- schéma métier SQLite ;
- tables `lots`, `etapes`, `jobs`, `artefacts`, `evenements`, `problemes` ;
- repositories métier ;
- `ArtifactStore` ;
- worker ;
- upload Excel ;
- upload images ;
- mapping ;
- diagnostic Excel web ;
- CSV ;
- package ;
- purge métier.

Ne pas créer de modules vides pour ces sujets.

### Règles non négociables

- Un comportement observable par ticket.
- Pas de route stub qui renvoie succès sans comportement réel.
- Pas de donnée réelle, Excel, zip, image, log ou artefact généré dans Git.
- Ne pas déplacer `sircom2026/excel_diagnostic.py`.
- Ne pas coder en dur `B_ID`, `F_ID` ni une position Excel 2025.
- Les chemins disque internes ne sortent pas par l'API.
- Ne pas revendiquer conformité RGAA ou DSFR complète.
- Le shell UI doit rester minimal : nom de l'application, navigation de base,
  zone de contenu, pas d'écran métier.

### Tests attendus

Commande ciblée à fournir en fin de session.

Tests minimum :

- valeurs config par défaut ;
- surcharge env ;
- valeur invalide ;
- `SIRCOM_MAX_ACTIVE_JOBS=1` ;
- `SIRCOM_DISK_FREE_MIN_MB=5120` ;
- `/health` ;
- `/health/ready` premier démarrage ;
- `/health/ready` data dir non inscriptible ;
- `/health/ready` disque sous le seuil et au seuil ;
- `/api/config/limits` ;
- `/docs` ou `/openapi.json`.

### Preuve finale attendue

Réponse finale concise avec :

- fichiers changés ;
- commande de test exécutée ;
- résultat de test ;
- confirmation que les tickets 02 à 23 n'ont pas été anticipés ;
- limites restantes s'il y en a.

### Critère de rejet

Le ticket est à refuser si le diff touche ou introduit une responsabilité aval :
lots, uploads, worker, artefacts métier, mapping, CSV, images, package ou purge.

