# Index des tickets Sircom 2026

Dernière mise à jour : 2026-07-28.

## Frontier active

La seule frontier agent immédiatement lançable est :

- [2026-07-28-05 — Rétablir le gate Ruff global](2026-07-28-fiabilisation-parcours-sircom-2026/05-retablir-gate-ruff-global.md).

La décision humaine InDesign peut être menée en parallèle :

- [2026-07-28-06 — Décider le contrat des champs InDesign 2026](2026-07-28-fiabilisation-parcours-sircom-2026/06-decider-contrat-champs-indesign-2026.md).

Le graphe complet, le checkpoint post-tickets d'activation de 06A et l'ordre de
reprise sont dans
[l'index de fiabilisation du 28 juillet](2026-07-28-fiabilisation-parcours-sircom-2026/README.md).

## Taxonomie

- `ready-for-agent` : contrat fermé, dépendances closes, exécutable maintenant ;
- `blocked` : contrat fermé, mais au moins une dépendance reste ouverte ;
- `ready-for-human` : décision ou vérification humaine lançable maintenant ;
- `conditional` : ticket activé uniquement par la décision explicitement citée ;
- `done` : livraison terminée ; ne pas réimplémenter ;
- `historical` : preuve de cadrage ou d'exécution, jamais une frontier.

Un ticket dont une dépendance n'est pas `done` ne peut pas être
`ready-for-agent`. Une décision métier ou de sécurité non écrite dans la spec
rend le ticket `blocked`.

## Historique

- [Tickets du 21 juillet](2026-07-21-sircom-2026/README.md) : livraisons
  historiques, non actives.
- [Chantier bornes ressources du 23 juillet](2026-07-23-chantier-a-bornes-ressources/README.md) :
  livraison historique, non active.
- [Plan monolithique du 21 juillet](2026-07-21-tickets-implementation-sircom-2026.md) :
  archive de cadrage, non exécutable.
