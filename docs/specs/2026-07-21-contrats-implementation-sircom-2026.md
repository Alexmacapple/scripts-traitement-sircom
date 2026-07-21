# Contrats complémentaires d'implémentation Sircom 2026

Date : 2026-07-21

## Rôle

Ce document ferme la passe de décisions demandée avant les tickets 03 et aval.
Il complète les trois specs déjà publiées :

- [Contrat fonctionnel](2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](2026-07-21-design-architecture-web-sircom-2026.md)

En cas de contradiction avec une question ouverte historique, les contrats
ci-dessous priment pour l'implémentation V1.

## Contrats normatifs

| Contrat | Fichier | Tickets couverts |
|---|---|---|
| UI DSFR | [design-ui-dsfr](2026-07-21-design-ui-dsfr-sircom-2026.md) | 01, 04, 06, 09, 11, 12, 15, 17, 18, 20, 22, 23 |
| Exécution, stockage, worker | [execution-stockage-worker](2026-07-21-contrat-execution-stockage-worker-sircom-2026.md) | 03, 04, 05, 06, 07, 08 |
| Données, CSV, images | [donnees-csv-images](2026-07-21-contrat-donnees-csv-images-sircom-2026.md) | 09, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22 |
| Exploitation, purge, traces | [exploitation-purge](2026-07-21-contrat-exploitation-purge-sircom-2026.md) | 02, 04, 05, 06, 21, 23 |

## Décisions fermées

- Le front V1 est un front serveur FastAPI/Jinja utilisant les assets DSFR
  statiques, sans SPA.
- Les écrans DSFR sont cadrés par vues, états, composants, messages et tests.
- Le schéma SQLite V1 est run-scopé : `run_id`, `idempotency_key`,
  `lease_version`, états d'artefacts, contraintes et index sont obligatoires.
- Le store d'artefacts a un protocole de commit atomique, de réconciliation au
  démarrage et de rejet des commits tardifs.
- Les statuts lot/étape/job et la matrice d'événements sont fixés.
- Le worker local a un contrat de lease, heartbeat, reclaim, fencing et arrêt
  gracieux.
- L'invalidation aval est gouvernée par un DAG et des fingerprints SHA-256 de
  JSON canonique versionné.
- Les profils de mapping, rôles logiques V1 et noms CSV sont définis sans
  persister de valeurs métier.
- Le flux CSV/images est décorrélé : CSV possible sans images confirmées,
  package avec images seulement depuis un snapshot `ImageBindings` courant.
- La sémantique `imageid` sans image est fixée.
- Les zips images refusent toute image en sous-dossier en V1, hors entrées
  techniques ignorables `__MACOSX/` et `.DS_Store`.
- Les rapports, logs, traces anonymisées, purge, indicateurs disque et
  rétention sont cadrés.

## Point externe non fermé

La compatibilité réelle avec le gabarit InDesign 2026 dépend d'une réponse
Sircom : le gabarit attend-il les nouveaux noms `id_dossier` et noms mappés, ou
réutilise-t-il les champs 2025 comme `b_id` et `a_madeinfr` ?

Décision V1 tant que la réponse manque :

- l'application garantit le format CSV 2025 prouvé au niveau octets ;
- elle ne promet pas que le gabarit InDesign 2026 importera les champs sans test
  manuel ;
- aucun adaptateur legacy de noms de champs n'est inventé dans les tickets.

## Effet sur les tickets

Les 23 tickets redeviennent `ready-for-agent` du point de vue cadrage. Leur
ouverture reste contrainte par le graphe de dépendances :

- frontier initiale : 01 ;
- après 01 : 02 et 03 ;
- ensuite : suivre strictement le graphe, une session agent par ticket.

Les agents d'implémentation doivent lire le contrat complémentaire applicable
avant de coder le ticket.

