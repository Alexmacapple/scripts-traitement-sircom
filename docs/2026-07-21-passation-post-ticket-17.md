# Passation Sircom 2026 - après ticket 17

Date : 2026-07-21.

## État courant

- Branche : `main`.
- Dernier commit fonctionnel poussé : `d6f9338 feat: ajouter apercu csv sircom`.
- Serveur local relancé avec le nouveau code : `http://127.0.0.1:8000/`.
- Session Uvicorn Codex active : `94472`, processus serveur `43869`.
- Smoke post-relance :
  - `GET /health` : 200 ;
  - `GET /` : 200.

## Ticket livré

Ticket 17 uniquement : aperçu CSV, validation humaine et export UTF-16.

Changements principaux :

- Nouveau module `sircom2026/csv_preview.py`.
- Routes API :
  - `GET /api/lots/{lot_id}/csv/preview` ;
  - `POST /api/lots/{lot_id}/csv/preview/validate` ;
  - `GET /api/lots/{lot_id}/csv/export`.
- UI DSFR ajoutée dans le détail de lot :
  - aperçu des en-têtes et premières lignes ;
  - compteurs lignes/colonnes ;
  - colonnes et lignes supprimées ;
  - alertes ;
  - bouton de validation humaine ;
  - lien de téléchargement du CSV final après validation.
- Export final écrit en artefact courant `csv_final`, téléchargeable par `artifact_id`.
- CSV final vérifié par le contrat InDesign existant.
- Export bloqué si les prérequis `export testable` ne sont pas réunis, si l'aperçu courant n'est pas validé, ou si un bloquant reste ouvert.
- Changement Excel, mapping ou tri invalide l'export validé.
- Rejeu d'une clé d'idempotence d'aperçu refusé si elle pointe vers un aperçu devenu obsolète.
- Images absentes/non finalisées signalées en alerte non bloquante.

## Vérifications exécutées

- `.venv/bin/python -m unittest tests.test_csv_preview` : OK, 3 tests.
- `.venv/bin/python -m unittest tests.test_csv_preview tests.test_csv_contract tests.test_sorting tests.test_normalization tests.test_invalidation tests.test_worker` : OK, 36 tests.
- `.venv/bin/python -m compileall -q sircom2026 tests` : OK.
- `git diff --cached --check` : OK avant commit.
- `.venv/bin/python -m unittest` : OK, 137 tests, 2 skipped.
- `env SIRCOM_RUN_PLAYWRIGHT=1 .venv/bin/python -m unittest tests.test_lots_playwright` : OK, 2 tests.
- `curl -sS -i http://127.0.0.1:8000/health` : 200.
- `curl -sS -i http://127.0.0.1:8000/` : 200.

## Revue

Review gate fait avant commit :

- Standards : aucun écart dur AGENTS.md. Un nettoyage appliqué : suppression d'une constante inutilisée.
- Spec : findings corrigés avant commit :
  - garde explicite des prérequis `export testable` ;
  - message images rendu durable sans affirmer à tort l'absence de zip ;
  - test UI HTML de l'aperçu/bouton/lien ;
  - test d'invalidation export après changement Excel, mapping ou tri ;
  - idempotence protégée contre les aperçus obsolètes.

Risque accepté : le module `csv_preview.py` reprend le style déjà présent dans `sorting.py` pour le cycle validation/job/artefact. Refactor partagé à éviter tant que les tickets aval ne stabilisent pas le pattern.

## Prochaine reprise

Frontier suivante : ticket 18 uniquement.

Ticket recommandé :

- `docs/tickets/2026-07-21-sircom-2026/18-upload-zip-images-et-inspection-securisee.md`

À lire avant de coder :

- `AGENTS.md`
- `docs/agents/issue-tracker.md` s'il existe ; au moment de cette passation, il était absent.
- `docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`
- `docs/specs/2026-07-21-contrats-implementation-sircom-2026.md`
- `docs/tickets/2026-07-21-sircom-2026/18-upload-zip-images-et-inspection-securisee.md`

Périmètre à respecter au ticket 18 :

- Upload zip images.
- Inspection sécurisée du zip.
- Refus zip slip, seuils taille/nombre/décompressé, sous-dossiers refusés sauf exceptions système documentées.
- Artefact source zip et rapport d'inspection.
- Pas de matching images, pas de traitement JPG final, pas de package final.

Point d'attention immédiat :

- Le ticket 17 signale aujourd'hui les images non finalisées en alerte non bloquante. Le ticket 18 devra commencer à faire disparaître ou préciser cette alerte quand un zip images valide sera disponible, sans rendre l'export CSV dépendant des images.

