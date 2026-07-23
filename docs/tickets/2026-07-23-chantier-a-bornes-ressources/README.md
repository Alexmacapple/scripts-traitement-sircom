# Tickets chantier A - Bornes ressources Sircom 2026

Date : 2026-07-23

Parent : [spec chantier A](../../specs/2026-07-23-chantier-a-bornes-ressources-sircom-2026.md).

Sources principales :

- [revue code Fable Flavien](../../audits/2026-07-23-revue-code-fable-flavien.md)
- [contre-revue GLM](../../audits/2026-07-23-contre-revue-glm.md)
- [contrat exécution, stockage et worker](../../specs/2026-07-21-contrat-execution-stockage-worker-sircom-2026.md)
- [contrat exploitation purge](../../specs/2026-07-21-contrat-exploitation-purge-sircom-2026.md)

Revue critique : [connu-inconnu et avocat du diable](revue-connus-inconnus-avocat-du-diable.md).

## Clôture

Statut global : `done`.

Commits livrés :

- `c32468c` - Expose configurable resource limits.
- `b1bb5f2` - Reject oversized Excel dimensions.
- `6d6f07e` - Reject oversized source images.
- `76cdf30` - Block heavy jobs on low disk.
- `8461083` - Add CI lint and adversarial image proof.

Preuves finales :

- `uv run --frozen --extra test ruff format --check .` : OK.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q` :
  244 tests passés, 5 ignorés, couverture 90,51 %.
- `env SIRCOM_RUN_PLAYWRIGHT=1 uv run --frozen --extra test python -m unittest tests.test_lots_playwright` :
  4 tests passés.

Mode d'exécution conseillé : un ticket par session, code modifié au minimum,
tests ciblés dans le ticket, puis statut Git.

## Frontier

Frontier initiale :

- 01 - Limites ressources configurables et visibles ;
- 04 - Garde disque avant jobs lourds.

Après 01 :

- 02 - Bornes Excel ;
- 03 - Bornes images.

Après 02, 03 et 04 :

- 05 - Preuves adversariales et Ruff check en CI.

## Tickets

| N | Statut | Ticket | Dépend de |
|---|---|---|---|
| 01 | `done` | [Limites ressources configurables et visibles](01-limites-ressources-configurables-et-visibles.md) | aucun, peut commencer immédiatement. |
| 02 | `done` | [Bornes Excel dimensions et diagnostic](02-bornes-excel-dimensions-et-diagnostic.md) | 01. |
| 03 | `done` | [Bornes images pixels et conversion](03-bornes-images-pixels-et-conversion.md) | 01. |
| 04 | `done` | [Garde disque avant jobs lourds](04-garde-disque-avant-jobs-lourds.md) | aucun, peut commencer immédiatement. |
| 05 | `done` | [Preuves adversariales et Ruff check en CI](05-preuves-adversariales-et-ruff-check-ci.md) | 02, 03, 04. |

## Règles globales

- Ne pas refactorer les gros modules hors besoin direct du ticket.
- Ne pas changer le format CSV InDesign ni le nom `export-jpg-resize/`.
- Ne pas coder en dur un chemin utilisateur.
- Les refus doivent être structurés avec codes stables et messages affichables.
- Les tests doivent utiliser des fichiers synthétiques temporaires, jamais de
  données réelles.
- Les seuils doivent rester configurables par variables `SIRCOM_*`.
