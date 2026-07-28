# 06A - Adapter les exports au contrat InDesign 2026

Statut : `conditional`

Dépend de : 01, 02, 03, 04, 05 et 06.

Condition d'activation : après clôture de 01 à 06, les schémas et CSV
synthétiques post-tickets sont comparés à l'oracle du ticket 06. Un écart sur
au moins un parcours consigné comme `06A activé` rend ce ticket lançable. En
l'absence d'écart, consigner `06A non activé` avec la preuve ; ne pas lancer ce
ticket.

À construire : adapter uniquement les parcours désignés par la décision 06 et
prouver le contrat sur un CSV synthétique non sensible avant toute recette
réelle.

## Contexte

Le ticket 06 est une décision humaine et exclut l'implémentation. Le ticket 07
est une recette et exclut toute correction. Ce ticket ferme la branche entre
les deux lorsque les champs attendus diffèrent des exports synthétiques
post-tickets.

## Critères d'acceptation

- [ ] Le checkpoint d'activation cite les SHA ou diffs post-tickets comparés et
      ne repose pas sur l'export préexistant au ticket 01.
- [ ] La décision datée du ticket 06 est citée et son dictionnaire de champs est
      reproduit comme oracle testable, sans donnée personnelle.
- [ ] Seuls les parcours déclarés non conformes par le checkpoint post-tickets
      sont modifiés.
- [ ] Le nom de la clé dossier, `imageid`, `@pathimg`, `#N/A`, l'ordre des
      champs, l'encodage UTF-16 avec BOM, la virgule et les fins de ligne LF
      correspondent exactement à la décision.
- [ ] Si le web et le script nécessitent des adaptateurs distincts, leurs
      contrats et tests restent explicitement séparés.
- [ ] Un CSV synthétique minimal est généré par chaque parcours modifié et
      vérifié au niveau octets et en-têtes.
- [ ] La fixture synthétique convenue au ticket 06 est importée ou approuvée
      dans le gabarit cible sans remapping improvisé.
- [ ] Les specs et documentations d'usage sont mises à jour pour supprimer
      l'ancienne divergence décidée, sans réécrire les preuves historiques.
- [ ] Aucun jeu officiel ni livrable réel n'est ouvert pendant
      l'implémentation.

## Hors périmètre

- Reprendre la décision métier du ticket 06.
- Modifier le gabarit InDesign.
- Corriger un autre défaut découvert hors de l'adaptation décidée.
- Modifier `scripts-2025/`.
- Exécuter la recette réelle du ticket 07.

## Preuve attendue

- décision 06 et oracle de champs ;
- tests ciblés des adaptateurs ;
- contrôle binaire et structurel des CSV synthétiques ;
- preuve d'import ou d'approbation de la fixture synthétique ;
- commandes Ruff et tests applicables ;
- `git diff --check`.

## Sources locales

- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `docs/tickets/2026-07-28-fiabilisation-parcours-sircom-2026/06-decider-contrat-champs-indesign-2026.md`
- décision écrite et datée du ticket 06
