# Tickets unitaires Sircom 2026 — archive livrée

Index actif : [tickets Sircom 2026](../README.md).

Plan de cadrage historique :
[2026-07-21-tickets-implementation-sircom-2026.md](../2026-07-21-tickets-implementation-sircom-2026.md).

Revue détaillée : [revue connu-inconnu et avocat du diable](revue-connus-inconnus-avocat-du-diable.md).
Revue post-cadrage : [retours ADHD intégrés](revue-adhd-post-cadrage.md).

Cette série est entièrement livrée. Elle sert de preuve historique et ne
contient aucune frontier active.

Note post-contrats complémentaires : le cadrage aval est publié dans
[les contrats complémentaires d'implémentation](../../specs/2026-07-21-contrats-implementation-sircom-2026.md).
Les indications de dépendance ci-dessous décrivent l'ordre de livraison
historique. Elles ne rendent aucun ticket relançable.

Statuts opérationnels mis à jour au 2026-07-28 :

- tickets 01 à 34 et tranches associées : `done` ;
- tranches 24B, 24C et 24D : livrées dans le parent 24.

| N | Statut | Ticket | Dépend de |
|---|---|---|---|
| 01 | `done` | [Socle FastAPI, configuration, santé et UI shell DSFR](01-socle-fastapi-configuration-sante-et-ui-shell-dsfr.md) | historique |
| 02 | `done` | [Politique d'accès locale et erreurs API structurées](02-politique-d-acces-locale-et-erreurs-api-structurees.md) | historique |
| 03 | `done` | [Schéma SQLite, migrations et repositories de base](03-schema-sqlite-migrations-et-repositories-de-base.md) | historique |
| 04 | `done` | [Lots, consultation, suppression logique et timeline UI](04-lots-consultation-suppression-logique-et-timeline-ui.md) | historique |
| 05 | `done` | [Store d'artefacts atomique et téléchargements par `artifact_id`](05-store-d-artefacts-atomique-et-telechargements-par-artifact-id.md) | historique |
| 06 | `done` | [Statuts métier, événements, problèmes structurés et logs séparés](06-statuts-metier-evenements-problemes-structures-et-logs-separes.md) | historique |
| 07 | `done` | [Worker local, file SQLite, idempotence et annulation](07-worker-local-file-sqlite-idempotence-et-annulation.md) | historique |
| 08 | `done` | [Retry et invalidation aval par fingerprints](08-retry-et-invalidation-aval-par-fingerprints.md) | historique |
| 09 | `done` | [Upload Excel sécurisé, limites et stockage artefact](09-upload-excel-securise-limites-et-stockage-artefact.md) | historique |
| 10 | `done` | [Diagnostic Excel persisté](10-diagnostic-excel-persiste.md) | historique |
| 11 | `done` | [Messages Excel sale et panneau problèmes UI](11-messages-excel-sale-et-panneau-problemes-ui.md) | historique |
| 12 | `done` | [Mapping par défaut, profils brouillon et validation humaine](12-mapping-par-defaut-profils-brouillon-et-validation-humaine.md) | historique |
| 13 | `done` | [Fusion multi-onglets](13-fusion-multi-onglets.md) | historique |
| 14 | `done` | [Normalisation contenu](14-normalisation-contenu.md) | historique |
| 15 | `done` | [Tri région/département et validation humaine](15-tri-region-departement-et-validation-humaine.md) | historique |
| 16 | `done` | [Vérificateur de contrat CSV InDesign](16-verificateur-de-contrat-csv-indesign.md) | historique |
| 17 | `done` | [Aperçu CSV, validation humaine et export UTF-16](17-apercu-csv-validation-humaine-et-export-utf-16.md) | historique |
| 18 | `done` | [Upload zip images et inspection sécurisée](18-upload-zip-images-et-inspection-securisee.md) | 05, 08. |
| 19 | `done` | [Spike formats images Mac/VPS](19-spike-formats-images-mac-vps.md) | 18. |
| 20 | `done` | [Matching et traitement images](20-matching-et-traitement-images.md) | historique |
| 21 | `done` | [Rapports métier et technique](21-rapports-metier-et-technique.md) | historique |
| 22 | `done` | [Package final, manifeste et téléchargements](22-package-final-manifeste-et-telechargements.md) | historique |
| 23 | `done` | [Purge, rétention, indicateurs disque et trace anonymisée](23-purge-retention-indicateurs-disque-et-trace-anonymisee.md) | historique |
| 24 | `done` | [Refactorisation progressive des fichiers volumineux](24-refactorisation-progressive-des-fichiers-volumineux.md) | aucun, peut commencer immédiatement. |
| 24A | `done` | [Inventaire imports et contrat public database.py](24a-inventaire-imports-et-contrat-public-database.md) | 24. |
| 25 | `done` | [Rendre Ruff global exploitable](25-rendre-ruff-global-exploitable.md) | aucun. |
| 26 | `done` | [Figer le format Ruff global](26-figer-le-format-ruff-global.md) | 25. |
| 27 | `done` | [Corriger le packaging des partials Jinja](27-corriger-packaging-partials-jinja.md) | aucun, peut commencer immédiatement. |
| 28 | `done` | [Ajouter un seuil de couverture en CI](28-ajouter-seuil-couverture-ci.md) | aucun, peut commencer immédiatement. |
| 29A | `done` | [Contrat public `image_matching.py`](29a-contrat-public-image-matching.md) | aucun, peut commencer immédiatement. |
| 29B | `done` | [Contrat public `mapping.py`](29b-contrat-public-mapping.md) | aucun, peut commencer immédiatement. |
| 29C | `done` | [Contrat public `api/lots.py`](29c-contrat-public-api-lots.md) | aucun, peut commencer immédiatement. |
| 29D | `done` | [Contrat public `reports.py`](29d-contrat-public-reports.md) | aucun, peut commencer immédiatement. |
| 30 | `done` | [Découper `image_matching.py` sans changer le comportement](30-decouper-image-matching-sans-changer-comportement.md) | 29A. |
| 31 | `done` | [Découper `mapping.py` sans changer le workflow mapping](31-decouper-mapping-sans-changer-workflow.md) | 29B. |
| 32 | `done` | [Découper `api/lots.py` sans changer les routes publiques](32-decouper-api-lots-sans-changer-routes.md) | 29C. |
| 33 | `done` | [Découper `reports.py` sans changer les rapports générés](33-decouper-reports-sans-changer-rapports.md) | 29D. |
| 34 | `done` | [Extraire la génération du zip images traitées](34-extraire-generation-zip-images-traitees.md) | 29A, 30. |
