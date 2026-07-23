# Tickets unitaires Sircom 2026

Index principal : [2026-07-21-tickets-implementation-sircom-2026.md](../2026-07-21-tickets-implementation-sircom-2026.md).

Revue détaillée : [revue connu-inconnu et avocat du diable](revue-connus-inconnus-avocat-du-diable.md).
Revue post-cadrage : [retours ADHD intégrés](revue-adhd-post-cadrage.md).

Frontier initiale : ticket 01 uniquement.

Note post-contrats complémentaires : le cadrage aval est publié dans
[les contrats complémentaires d'implémentation](../../specs/2026-07-21-contrats-implementation-sircom-2026.md).
Les tickets non livrés restent `ready-for-agent` du point de vue cadrage.
L'ouverture reste contrainte par le graphe : ticket 01 d'abord, puis 02 et 03
après livraison du ticket 01.

Statuts opérationnels mis à jour au 2026-07-23 :

- tickets 18, 19, 24, 24A et 25 : `done` ;
- tranches 24B, 24C et 24D : livrées dans le parent 24 ;
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
