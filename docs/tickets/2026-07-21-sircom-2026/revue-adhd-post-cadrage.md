# Revue ADHD post-cadrage - Sircom 2026

Statut : note de traçabilité.

Cette note trace les retours issus de la passe ADHD manuelle lancée après le
cadrage `cuisine-moi`, les specs et la revue connu-inconnu / avocat du diable.
Elle ne remplace ni les specs ni les tickets. Elle sert à distinguer ce qui
était déjà couvert, ce qui était partiel, et le delta réellement ajouté.

Règle d'intégration : ne pas créer de nouveau ticket quand un ticket existant
porte déjà le comportement ; ajouter seulement un critère testable si le delta
réduit un risque concret.

| Retour ADHD | État actuel | Preuve source | Décision |
|---|---|---|---|
| Tripwire "pas d'auth seulement si loopback" | Partiel | Ticket 01 fixe le lancement local sur `127.0.0.1` ; la spec architecture fixe `SIRCOM_BIND_HOST=127.0.0.1` ; ticket 02 prévoit une `AccessPolicy` locale sans authentification. | Ajouter au ticket 02 un critère explicite : la tolérance sans auth ne vaut que pour un host loopback ; un host exposé sans auth doit être refusé par configuration ou politique. |
| Capsule incident | Partiel, suffisamment couvert pour la V1 | Ticket 06 sépare événements techniques et problèmes métier ; ticket 21 prévoit `rapport-technique.json` avec durées, tailles, compteurs, codes erreur et traces anonymisées ; ticket 23 conserve une trace anonymisée après purge. | Ne pas créer de nouvelle feature. Pendant le ticket 21, interpréter le rapport technique comme la capsule incident minimale, sans valeurs métier. |
| Sentinelles de confidentialité | Partiel, déjà orienté tests | Ticket 02 interdit les erreurs divulguant chemins ou données d'un autre lot ; ticket 21 exige des tests négatifs sur rapport technique et logs ; ticket 23 interdit chemins complets, noms originaux et valeurs de cellules dans la trace anonymisée. | Pas de nouveau ticket. Les tests des tickets 02, 21 et 23 doivent utiliser des valeurs synthétiques reconnaissables pour prouver l'absence de fuite. |
| Dérive specs / tickets / schéma | Hors produit V1 | Le master tickets et le README portent le graphe ; les specs portent les contrats ; aucun comportement utilisateur n'est attendu dans l'application. | Traiter comme contrôle de passation ou revue agent, pas comme fonctionnalité applicative. Premier point concret : revue lecture seule avant ouverture du ticket 04, après livraison des tickets 01, 02 et 03, pour vérifier que tickets, schéma SQLite, OpenAPI et specs ne divergent pas. |

## Delta retenu

Le seul patch documentaire immédiat est le tripwire loopback dans le ticket 02.
Les autres retours restent dans cette note pour conserver leur origine et éviter
de les réinventer comme tickets transverses.

## Contrôle de dérive

Avant ouverture du ticket 04, demander une revue agent lecture seule après les
tickets 01, 02 et 03. La revue doit comparer les specs, tickets, schéma SQLite
et OpenAPI produits, puis rendre un verdict court : `cohérent`, `écart mineur`
ou `écart bloquant`.

## Prompt de revue agents

```text
Contexte : projet Sircom 2026 / Made in France. Une passe ADHD post-cadrage a
proposé quatre garde-fous : tripwire "pas d'auth seulement si loopback",
capsule incident, sentinelles de confidentialité, contrôle de dérive
specs/tickets/schéma.

Mission : relire la note `docs/tickets/2026-07-21-sircom-2026/revue-adhd-post-cadrage.md`
et les tickets cités, puis dire si l'intégration est correcte.

Contraintes :
- ne modifier aucun fichier ;
- vérifier que les deltas ADHD sont traçables ;
- signaler tout doublon inutile ou critère manquant ;
- distinguer produit V1, tests, exploitation et contrôle de passation.

Sortie attendue : matrice courte `garde-fou / verdict / preuve / correction
minimale proposée`.
```
