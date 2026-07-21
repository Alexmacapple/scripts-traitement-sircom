# Tickets unitaires Sircom 2026

Index principal : [2026-07-21-tickets-implementation-sircom-2026.md](../2026-07-21-tickets-implementation-sircom-2026.md).

Revue détaillée : [revue connu-inconnu et avocat du diable](revue-connus-inconnus-avocat-du-diable.md).

Frontier initiale : ticket 01 uniquement.

| N | Ticket | Dépend de |
|---|---|---|
| 01 | [Socle FastAPI, configuration, santé et UI shell DSFR](01-socle-fastapi-configuration-sante-et-ui-shell-dsfr.md) | aucun, peut commencer immédiatement. |
| 02 | [Politique d'accès locale et erreurs API structurées](02-politique-d-acces-locale-et-erreurs-api-structurees.md) | 01. |
| 03 | [Schéma SQLite, migrations et repositories de base](03-schema-sqlite-migrations-et-repositories-de-base.md) | 01. |
| 04 | [Lots, consultation, suppression logique et timeline UI](04-lots-consultation-suppression-logique-et-timeline-ui.md) | 02, 03. |
| 05 | [Store d'artefacts atomique et téléchargements par `artifact_id`](05-store-d-artefacts-atomique-et-telechargements-par-artifact-id.md) | 02, 03, 04. |
| 06 | [Statuts métier, événements, problèmes structurés et logs séparés](06-statuts-metier-evenements-problemes-structures-et-logs-separes.md) | 03, 04. |
| 07 | [Worker local, file SQLite, idempotence et annulation](07-worker-local-file-sqlite-idempotence-et-annulation.md) | 05, 06. |
| 08 | [Retry et invalidation aval par fingerprints](08-retry-et-invalidation-aval-par-fingerprints.md) | 07. |
| 09 | [Upload Excel sécurisé, limites et stockage artefact](09-upload-excel-securise-limites-et-stockage-artefact.md) | 05, 08. |
| 10 | [Diagnostic Excel persisté](10-diagnostic-excel-persiste.md) | 09. |
| 11 | [Messages Excel sale et panneau problèmes UI](11-messages-excel-sale-et-panneau-problemes-ui.md) | 06, 10. |
| 12 | [Mapping par défaut, profils brouillon et validation humaine](12-mapping-par-defaut-profils-brouillon-et-validation-humaine.md) | 11. |
| 13 | [Fusion multi-onglets](13-fusion-multi-onglets.md) | 12. |
| 14 | [Normalisation contenu](14-normalisation-contenu.md) | 13. |
| 15 | [Tri région/département et validation humaine](15-tri-region-departement-et-validation-humaine.md) | 14. |
| 16 | [Vérificateur de contrat CSV InDesign](16-verificateur-de-contrat-csv-indesign.md) | 14. |
| 17 | [Aperçu CSV, validation humaine et export UTF-16](17-apercu-csv-validation-humaine-et-export-utf-16.md) | 15, 16. |
| 18 | [Upload zip images et inspection sécurisée](18-upload-zip-images-et-inspection-securisee.md) | 05, 08. |
| 19 | [Spike formats images Mac/VPS](19-spike-formats-images-mac-vps.md) | 18. |
| 20 | [Matching et traitement images](20-matching-et-traitement-images.md) | 12, 18, 19. |
| 21 | [Rapports métier et technique](21-rapports-metier-et-technique.md) | 17, 20. |
| 22 | [Package final, manifeste et téléchargements](22-package-final-manifeste-et-telechargements.md) | 17, 20, 21. |
| 23 | [Purge, rétention, indicateurs disque et trace anonymisée](23-purge-retention-indicateurs-disque-et-trace-anonymisee.md) | 22. |
