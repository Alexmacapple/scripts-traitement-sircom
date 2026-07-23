# Synthèse de vérification globale Sircom 2026

Date : 2026-07-21

Sources :

- `docs/audits/2026-07-21-verification-globale-sircom-2026-glm.md`
- `docs/audits/2026-07-21-verification-globale-sircom-2026-sol.md`
- retour GLM post-SOL transmis par Alex
- relecture Codex ciblée des specs et tickets touchés

SEMIOTIC-PROBE : NA. Synthèse opérationnelle de rapports techniques locaux.

Score de convergence formel : non calculé, aucun nouveau round multi-LLM n'a été
lancé. Convergence opérationnelle : forte après retour GLM post-SOL.

## Décision actionnable

- Verdict courant post-contrats complémentaires : **GO ticket 01**.
- Frontier exécutable : **`{01}` uniquement**, car les dépendances de code aval
  ne sont pas encore livrées.
- Corrections bloquantes restantes avant ticket 01 : **0**.
- Corrections structurantes restantes avant tickets aval : **0 côté cadrage**,
  fermées par les contrats complémentaires.
- Nouveau ticket à créer : **non**. Le découpage en 23 tickets est conservé.
- Discipline d'implémentation : une session agent par ticket, frontier stricte,
  pas d'anticipation des tickets aval.

## Arbitrage

SOL devient le backbone de la décision : son `STOP avant implémentation` était
justifié pour l'état documentaire initial, notamment sur les defaults V1, la
readiness, le schéma run-scopé, le worker, les artefacts, le cycle images/CSV et
la purge.

GLM apporte deux compléments utiles :

- le risque externe InDesign : le format CSV 2025 est prouvé, mais pas la
  compatibilité des noms de colonnes avec le gabarit 2026 ;
- la règle de nettoyage des en-têtes doit être écrite comme critère testable du
  ticket 12.

Codex arbitre ainsi : on ne casse pas le découpage. Les décisions structurantes
sont publiées dans
`docs/specs/2026-07-21-contrats-implementation-sircom-2026.md`; les agents
d'implémentation doivent les lire avec le ticket concerné.

## Patch P0 appliqué

Le patch P0 ferme les oracles nécessaires au ticket 01 :

- defaults V1 complets dans l'architecture ;
- `SIRCOM_MAX_ACTIVE_JOBS=1` ;
- `SIRCOM_DISK_FREE_MIN_MB=5120` ;
- `/health/ready` défini par configuration valide, data dir créable et
  inscriptible, `SELECT 1` SQLite au premier démarrage, seuil disque et réponse
  503 avec code stable ;
- tests attendus sur premier démarrage, data dir non inscriptible, disque sous
  seuil et disque au seuil.

Effet : ticket 01 est désormais lançable sans laisser un agent choisir les
valeurs ou la sémantique readiness.

## Corrections consensuelles appliquées

- `id_dossier`, `imageid` et `@pathimg` sont explicitement les exceptions V1 au
  renommage 2025.
- Le ticket 12 porte la règle complète de nettoyage des en-têtes et un test sur
  un nom accentué de plus de 10 caractères.
- Les images en sous-dossiers de zip sont refusées en V1 ; seuls `__MACOSX/` et
  `.DS_Store` peuvent être ignorés sans bloquer.
- Les téléchargements par `artifact_id` retournent publiquement 404 pour artefact
  absent, supprimé, obsolète ou appartenant à un autre lot.
- Les tickets 02 et 05 portent le test d'indistinction publique 404.
- La route `DELETE /api/lots/{lot_id}` est alignée sur le ticket 04 : elle pose
  une suppression logique/tombstone. Si un job actif doit s'arrêter, elle répond
  202 et déclenche l'annulation coopérative ; la purge physique reste portée par
  le ticket 23.
- Les index de tickets signalent que seul le ticket 01 est exécutable tant que
  la passe aval n'est pas fermée.

## Décisions fermées par contrats complémentaires

Statut post-contrats complémentaires : décisions fermées par :

- `docs/specs/2026-07-21-design-ui-dsfr-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-execution-stockage-worker-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-exploitation-purge-sircom-2026.md`

La table ci-dessous est conservée comme trace de la revue qui a déclenché les
contrats.

| Échéance de la revue initiale | Tickets concernés | Décision désormais publiée |
|---|---|---|
| Avant 03 | 03, 05, 06, 07, 08 | Schéma run-scopé : `run_id`, idempotency key, `lease_version`, états artefacts, contraintes uniques et index. |
| Avant 05 | 05, 07, 08, 22, 23 | Store d'artefacts : protocole de commit atomique, réconciliation au démarrage, quarantaine/suppression des fichiers sans ligne, obsolescence des lignes sans fichier ou hash invalide, rejet des commits tardifs par `run_id + lease_version`. |
| Avant 04/06 | 04, 06, 08 | Matrice exhaustive `statut + événement -> statut suivant`, y compris annulation, invalidation et purge. |
| Avant 07 | 07 | Worker : TTL de lease, heartbeat, reclaim, compare-and-set, stratégie SQLite et arrêt gracieux. |
| Avant 08 | 08 | DAG d'invalidation complet et fingerprints SHA-256 de JSON canonique versionné. |
| Avant 12 | 12, 14, 15, 20 | Profils de mapping, rôles logiques V1, édition des noms CSV et persistance hors valeurs métier. |
| Avant 15 | 15, 17 | Ordre source stable après union multi-onglets, comparateur région/département et vides en fin. |
| Avant 16/17/22 | 16, 17, 22 | Clarification Sircom sur le gabarit InDesign 2026 et les noms de champs attendus. |
| Avant 17/20/22 | 17, 20, 22 | Snapshot `ImageBindings`, sémantique de `imageid` sans image et invalidation du CSV après changement image. |
| Avant 18/20 | 18, 20 | Inspection images en worker, progression, annulation, action "continuer sans images" et niveaux de matching. |
| Avant 21/23 | 21, 23 | Allowlist logs/trace, nom original du zip avant purge seulement, compteurs rapport et trace anonymisée. |
| Avant 22 | 22 | Manifeste non auto-référentiel et schéma `mapping-utilise.json`. |
| Avant 23 | 23 | Déclencheur de purge automatique, cadence, durée de trace anonymisée et indicateurs disque complets. |

## Point image/CSV

Ne pas régler ce point par une dépendance mécanique `17 -> 20` sans décision
produit. Le flux cible doit distinguer :

- CSV possible sans images si l'utilisateur confirme "continuer sans images" ;
- CSV/package final avec images seulement depuis un snapshot `ImageBindings`
  courant ;
- toute modification de zip, matching ou résolution invalide aperçu CSV, CSV
  final, rapports et package.

Décision publiée dans le contrat données/CSV/images : conserver `imageid`
déterministe pour toute ligne avec `id_dossier` valide, et laisser `@pathimg`
vide lorsqu'aucune image n'est retenue.

## Verdict par phase

- Maintenant : implémenter **ticket 01 uniquement**.
- Après ticket 01 : ouvrir 02 et 03 possible.
- Avant chaque ticket : lire le contrat complémentaire applicable.
- Avant package : obtenir la réponse Sircom sur le gabarit InDesign 2026 ou
  documenter explicitement que le test InDesign réel reste hors automatisation.

## Preuves

- GLM et SOL confirment le graphe : 23 tickets, 36 dépendances, acyclique.
- SOL a produit les preuves Excel : 5 tests diagnostic passés, `Sircom2.xlsx`
  accepté, `Sircom1.xlsx` refusé pour colonnes masquées et formules.
- SOL a vérifié le CSV 2025 au niveau octets : UTF-16LE avec BOM `FF FE`, LF,
  80 en-têtes, zéro `#N/A`/`N/C`, `imageid` et `@pathimg` aux positions attendues.
- GLM post-SOL a confirmé ses angles morts et rejoint le verdict "GO ticket 01
  après P0".

## Limites

- Pas de vérification InDesign réelle : le gabarit 2026 reste une dépendance
  externe.
- Pas de fichier Excel 2026 réel disponible.
- Pas d'implémentation runtime à vérifier pour worker, SQLite concurrente,
  artefacts, purge, téléchargements ou pression disque.
- Le gabarit InDesign 2026 reste externe : la V1 garantit le format CSV, pas la
  validation automatique dans le gabarit réel.
