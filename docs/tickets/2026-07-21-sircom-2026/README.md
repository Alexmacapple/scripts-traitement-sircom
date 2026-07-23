# Tickets unitaires Sircom 2026

Index principal : [2026-07-21-tickets-implementation-sircom-2026.md](../2026-07-21-tickets-implementation-sircom-2026.md).

Revue détaillée : [revue connu-inconnu et avocat du diable](revue-connus-inconnus-avocat-du-diable.md).
Revue post-cadrage : [retours ADHD intégrés](revue-adhd-post-cadrage.md).

Frontier produit initiale : ticket 01 uniquement.
Frontier qualité 18+ : tickets 26, 27, 28, 29A, 29B, 29C et 29D.

Note post-contrats complémentaires : le cadrage aval est publié dans
[les contrats complémentaires d'implémentation](../../specs/2026-07-21-contrats-implementation-sircom-2026.md).
Les tickets non livrés restent `ready-for-agent` du point de vue cadrage.
L'ouverture reste contrainte par le graphe : ticket 01 d'abord, puis 02 et 03
après livraison du ticket 01.

Statuts opérationnels mis à jour au 2026-07-23 :

- tickets 18, 19, 24, 24A et 25 : `done` ;
- tranches 24B, 24C et 24D : livrées dans le parent 24 ;
- tickets 26, 28 à 33 : `ready-for-agent`, issus de l'évaluation qualité 16,5/20
  et découpés avec contrats préalables pour limiter la friction LLM ;
- ticket 27 : `done` ;
- tous les autres tickets listés : `ready-for-agent`.

| N | Statut | Ticket | Dépend de |
|---|---|---|---|
| 01 | `ready-for-agent` | [Socle FastAPI, configuration, santé et UI shell DSFR](01-socle-fastapi-configuration-sante-et-ui-shell-dsfr.md) | aucun, peut commencer immédiatement. |
| 02 | `ready-for-agent` | [Politique d'accès locale et erreurs API structurées](02-politique-d-acces-locale-et-erreurs-api-structurees.md) | 01. |
| 03 | `ready-for-agent` | [Schéma SQLite, migrations et repositories de base](03-schema-sqlite-migrations-et-repositories-de-base.md) | 01. |
| 04 | `ready-for-agent` | [Lots, consultation, suppression logique et timeline UI](04-lots-consultation-suppression-logique-et-timeline-ui.md) | 02, 03. |
| 05 | `ready-for-agent` | [Store d'artefacts atomique et téléchargements par `artifact_id`](05-store-d-artefacts-atomique-et-telechargements-par-artifact-id.md) | 02, 03, 04. |
| 06 | `ready-for-agent` | [Statuts métier, événements, problèmes structurés et logs séparés](06-statuts-metier-evenements-problemes-structures-et-logs-separes.md) | 03, 04. |
| 07 | `ready-for-agent` | [Worker local, file SQLite, idempotence et annulation](07-worker-local-file-sqlite-idempotence-et-annulation.md) | 05, 06. |
| 08 | `ready-for-agent` | [Retry et invalidation aval par fingerprints](08-retry-et-invalidation-aval-par-fingerprints.md) | 07. |
| 09 | `ready-for-agent` | [Upload Excel sécurisé, limites et stockage artefact](09-upload-excel-securise-limites-et-stockage-artefact.md) | 05, 08. |
| 10 | `ready-for-agent` | [Diagnostic Excel persisté](10-diagnostic-excel-persiste.md) | 09. |
| 11 | `ready-for-agent` | [Messages Excel sale et panneau problèmes UI](11-messages-excel-sale-et-panneau-problemes-ui.md) | 06, 10. |
| 12 | `ready-for-agent` | [Mapping par défaut, profils brouillon et validation humaine](12-mapping-par-defaut-profils-brouillon-et-validation-humaine.md) | 11. |
| 13 | `ready-for-agent` | [Fusion multi-onglets](13-fusion-multi-onglets.md) | 12. |
| 14 | `ready-for-agent` | [Normalisation contenu](14-normalisation-contenu.md) | 13. |
| 15 | `ready-for-agent` | [Tri région/département et validation humaine](15-tri-region-departement-et-validation-humaine.md) | 14. |
| 16 | `ready-for-agent` | [Vérificateur de contrat CSV InDesign](16-verificateur-de-contrat-csv-indesign.md) | 14. |
| 17 | `ready-for-agent` | [Aperçu CSV, validation humaine et export UTF-16](17-apercu-csv-validation-humaine-et-export-utf-16.md) | 15, 16. |
| 18 | `done` | [Upload zip images et inspection sécurisée](18-upload-zip-images-et-inspection-securisee.md) | 05, 08. |
| 19 | `done` | [Spike formats images Mac/VPS](19-spike-formats-images-mac-vps.md) | 18. |
| 20 | `ready-for-agent` | [Matching et traitement images](20-matching-et-traitement-images.md) | 12, 18, 19. |
| 21 | `ready-for-agent` | [Rapports métier et technique](21-rapports-metier-et-technique.md) | 17, 20. |
| 22 | `ready-for-agent` | [Package final, manifeste et téléchargements](22-package-final-manifeste-et-telechargements.md) | 17, 20, 21. |
| 23 | `ready-for-agent` | [Purge, rétention, indicateurs disque et trace anonymisée](23-purge-retention-indicateurs-disque-et-trace-anonymisee.md) | 22. |
| 24 | `done` | [Refactorisation progressive des fichiers volumineux](24-refactorisation-progressive-des-fichiers-volumineux.md) | aucun, peut commencer immédiatement. |
| 24A | `done` | [Inventaire imports et contrat public database.py](24a-inventaire-imports-et-contrat-public-database.md) | 24. |
| 25 | `done` | [Rendre Ruff global exploitable](25-rendre-ruff-global-exploitable.md) | aucun. |
| 26 | `ready-for-agent` | [Figer le format Ruff global](26-figer-le-format-ruff-global.md) | 25. |
| 27 | `done` | [Corriger le packaging des partials Jinja](27-corriger-packaging-partials-jinja.md) | aucun, peut commencer immédiatement. |
| 28 | `ready-for-agent` | [Ajouter un seuil de couverture en CI](28-ajouter-seuil-couverture-ci.md) | aucun, peut commencer immédiatement. |
| 29A | `ready-for-agent` | [Contrat public `image_matching.py`](29a-contrat-public-image-matching.md) | aucun, peut commencer immédiatement. |
| 29B | `ready-for-agent` | [Contrat public `mapping.py`](29b-contrat-public-mapping.md) | aucun, peut commencer immédiatement. |
| 29C | `ready-for-agent` | [Contrat public `api/lots.py`](29c-contrat-public-api-lots.md) | aucun, peut commencer immédiatement. |
| 29D | `ready-for-agent` | [Contrat public `reports.py`](29d-contrat-public-reports.md) | aucun, peut commencer immédiatement. |
| 30 | `ready-for-agent` | [Découper `image_matching.py` sans changer le comportement](30-decouper-image-matching-sans-changer-comportement.md) | 29A. |
| 31 | `ready-for-agent` | [Découper `mapping.py` sans changer le workflow mapping](31-decouper-mapping-sans-changer-workflow.md) | 29B. |
| 32 | `ready-for-agent` | [Découper `api/lots.py` sans changer les routes publiques](32-decouper-api-lots-sans-changer-routes.md) | 29C. |
| 33 | `ready-for-agent` | [Découper `reports.py` sans changer les rapports générés](33-decouper-reports-sans-changer-rapports.md) | 29D. |
