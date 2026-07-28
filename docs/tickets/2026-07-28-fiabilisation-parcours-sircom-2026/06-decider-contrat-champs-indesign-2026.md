# 06 - Décider le contrat des champs InDesign 2026

Statut : `ready-for-human`

Dépend de : aucun, peut commencer immédiatement.

À décider : le Sircom confirme les noms de champs et le gabarit InDesign 2026
qui constituent la cible de recette des deux parcours.

## Contexte

Les contrats actuels garantissent le format binaire du CSV mais déclarent
explicitement que la compatibilité des noms de champs avec le gabarit InDesign
2026 n'est pas fermée. Deux options restent visibles : nouveaux noms
`id_dossier` et noms mappés, ou réemploi de champs historiques tels que `b_id`
et `a_madeinfr`.

Cette décision ne doit pas être inventée par un agent. Elle conditionne la
recette réelle du ticket 07. Elle fixe une cible indépendante des exports
actuels, car le script sera encore modifié par les tickets 02 et 01.

## Critères de décision

- [ ] La version exacte du gabarit InDesign cible est identifiée.
- [ ] La liste des champs obligatoires, facultatifs et ignorés est fournie sans
      donnée personnelle.
- [ ] Le nom attendu pour la clé dossier est décidé.
- [ ] Le comportement attendu pour `imageid`, `@pathimg` et `#N/A` est confirmé.
- [ ] Le séparateur, l'encodage UTF-16, le BOM et les fins de ligne LF sont
      confirmés ou corrigés explicitement.
- [ ] La décision précise si les deux parcours suivent le même dictionnaire de
      champs ou des adaptateurs distincts.
- [ ] La décision fournit un oracle structurel permettant, après les tickets 01
      à 05, de comparer les deux exports sans interprétation supplémentaire.
- [ ] Un CSV minimal synthétique et non sensible est accepté comme fixture de
      recette.
- [ ] La décision est reportée dans les contrats versionnés avant toute
      adaptation de code.
- [ ] Les écarts avec le format 2025 sont listés comme décisions, pas comme
      hypothèses.

## Hors périmètre

- Implémenter l'adaptateur éventuellement décidé.
- Exécuter le jeu officiel.
- Inventer un mapping en l'absence du responsable Sircom.
- Modifier le gabarit InDesign.

## Preuve attendue

- décision écrite et datée ;
- oracle structurel utilisable au checkpoint d'activation de 06A ;
- référence au gabarit cible ;
- dictionnaire de champs validé ;
- fixture CSV synthétique importée ou approuvée par le responsable Sircom.

## Sources locales

- `TODO.md`
- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `docs/specs/2026-07-21-contrats-implementation-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`
- `re-run-old-script-2026/docs/sources.md`
