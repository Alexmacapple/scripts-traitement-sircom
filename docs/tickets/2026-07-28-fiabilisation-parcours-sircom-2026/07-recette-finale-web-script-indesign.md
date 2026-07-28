# 07 - Recetter les deux parcours sur le jeu officiel et dans InDesign

Statut : `blocked`

Dépend de : 01, 02, 03, 04, 05 et 06 ; 06A s'il est activé.

À vérifier : le parcours web et la voie scriptée sont exécutés séparément sur le
jeu officiel autorisé, puis leurs livrables sont contrôlés selon leurs contrats
et importés dans le gabarit InDesign décidé.

## Contexte

L'audit du 2026-07-28 a exercé le web avec des données synthétiques et contrôlé
les agrégats d'une ancienne sortie scriptée. Il n'a ni retraité le jeu officiel,
ni lancé le script courant avec `--clean`, ni importé le résultat dans InDesign.

Ce ticket est le gate humain final. Il ne doit commencer qu'après clôture des
cinq tickets agent, de la décision InDesign et de 06A s'il a été activé, avec
une autorisation explicite de traiter les données réelles.

## Critères d'acceptation

- [ ] L'autorisation de traiter le jeu officiel et le dossier de sortie est
      enregistrée avant l'exécution.
- [ ] Le SHA, la branche, le working tree, Python et les dépendances sont
      consignés sans modifier les changements préexistants.
- [ ] Le parcours web traite un lot Excel + ZIP jusqu'au téléchargement du
      package final.
- [ ] La voie scriptée exécute son orchestrateur avec `--clean` dans son dossier
      de sortie daté et contrôlé.
- [ ] Les deux CSV sont vérifiés sur l'encodage UTF-16, BOM, virgule, LF,
      absence de cellules métier vides, `#N/A`, tri, `imageid` et `@pathimg`.
      Le `@pathimg` web vide sans image finale est contrôlé comme l'exception
      système documentée, pas comme une cellule métier vide.
- [ ] La fusion des deux onglets est contrôlée par agrégats : union des
      identifiants, lignes communes et exclusives, colonnes et provenance.
- [ ] Les images absentes restent des alertes non bloquantes et les images
      produites respectent le contrat JPG.
- [ ] Le package web contient CSV, mapping, rapports, images attendues et
      manifeste cohérent.
- [ ] La voie scriptée contient CSV, images, mapping, résumé et rapports prévus
      par sa propre documentation ; l'absence de package web équivalent n'est
      pas traitée comme un défaut.
- [ ] Les CSV ou packages candidats sont importés dans le gabarit InDesign
      validé au ticket 06.
- [ ] La recette utilise les seuils et contrats livrés ; un ajustement ou une
      correction découvert ici ouvre un nouveau ticket et impose une nouvelle
      recette, sans modification silencieuse pendant celle-ci.
- [ ] Un échantillon convenu de champs, images, valeurs absentes et caractères
      accentués est contrôlé visuellement.
- [ ] Le rapport de recette n'expose aucune donnée personnelle ni valeur métier
      sensible ; il utilise des agrégats et exemples synthétiques.
- [ ] Un verdict distinct `GO`, `GO CONDITIONNEL` ou `NO-GO` est prononcé pour
      chaque parcours avec les écarts restants.

## Hors périmètre

- Corriger un défaut découvert pendant la recette dans ce même ticket.
- Publier les données ou livrables réels dans Git.
- Exiger une identité binaire entre le web et la voie scriptée.
- Modifier `scripts-2025/`.

## Preuve attendue

- commandes exécutées et codes de sortie ;
- agrégats CSV et images sans données sensibles ;
- inventaire du package web et des sorties scriptées ;
- compte rendu d'import InDesign ;
- état Git final démontrant l'absence d'artefacts suivis ;
- verdict séparé des deux parcours.

## Sources locales

- `AGENTS.md`
- `README.md`
- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `re-run-old-script-2026/README.md`
- `re-run-old-script-2026/docs/`
- décision du ticket 06
- ticket 06A s'il est activé
