# Index normatif des spécifications Sircom 2026

Dernière mise à jour : 2026-07-28.

## Contrat courant

La spécification active de fiabilisation est :

- [Fiabilisation des parcours Sircom 2026 avant usage réel](2026-07-28-fiabilisation-parcours-sircom-2026.md).

Elle amende les contrats du 21 et du 23 juillet uniquement pour les sujets
qu'elle cite explicitement : fusion scriptée, identifiants, archive OOXML,
normalisation `imageid`, confidentialité des journaux, gate Ruff, décision
InDesign et recette réelle.
Les autres clauses des contrats de base restent applicables.

## Ordre de préséance

Pour un même sujet :

1. `AGENTS.md` fixe les garde-fous de mission et de sécurité ;
2. ce fichier désigne la spec courante ;
3. la spec courante prime sur les clauses plus anciennes qu'elle amende
   explicitement ;
4. les contrats du 21 et du 23 juillet restent la base pour le reste ;
5. un ticket découpe une modification mais ne peut pas inventer ni remplacer
   une règle de spec.

Si deux textes de même rang restent incompatibles, l'implémentation est
`blocked` jusqu'à correction documentaire. Le code ou un test existant prouve
un comportement observé, pas la règle cible à lui seul.

## Contrats de base

- [Contrats d'implémentation](2026-07-21-contrats-implementation-sircom-2026.md)
- [Contrat fonctionnel](2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Contrat données, CSV et images](2026-07-21-contrat-donnees-csv-images-sircom-2026.md)
- [Contrat exécution, stockage et worker](2026-07-21-contrat-execution-stockage-worker-sircom-2026.md)
- [Contrat exploitation et purge](2026-07-21-contrat-exploitation-purge-sircom-2026.md)
- [Contrat UI DSFR](2026-07-21-design-ui-dsfr-sircom-2026.md)
- [Architecture web — référence historique et explicative](2026-07-21-design-architecture-web-sircom-2026.md)
- [Orchestration — référence historique et explicative](2026-07-21-orchestration-sircom-2026.md)
- [Bornes ressources](2026-07-23-chantier-a-bornes-ressources-sircom-2026.md)

Les descriptions au futur ou « à implémenter » dans les documents historiques
ne rouvrent aucun ticket marqué `done`. L'état actif du backlog est publié dans
`docs/tickets/README.md`.
