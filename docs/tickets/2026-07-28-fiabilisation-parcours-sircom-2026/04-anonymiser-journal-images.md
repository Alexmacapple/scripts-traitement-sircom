# 04 - Anonymiser le journal de traitement des images

Statut : `blocked`

Dépend de : 05. Commencer seulement quand 05 est `done`.

À construire : la voie scriptée produit une trace technique exploitable sans
identifiant dossier ni nom d'image métier brut, tout en conservant un rapport
local actionnable pour les images absentes ou ambiguës.

## Contexte

Le journal image scripté persiste actuellement des identifiants dossier, noms
d'images source, candidats ambigus et noms finaux. Il est présenté comme une
sortie utile de la chaîne et peut donc être conservé ou transmis avec les
livrables.

Les alertes d'images absentes doivent rester non bloquantes et visibles. La
correction doit séparer ce besoin métier de la trace technique standard, pas
supprimer l'information nécessaire à l'opérateur.

## Critères d'acceptation

- [ ] Le journal technique standard ne contient aucun identifiant dossier brut,
      nom d'image source ou final, chemin métier, valeur de cellule ni liste
      brute de candidats.
- [ ] Les événements techniques utilisent des codes stables, compteurs et
      références opaques propres au run, `img-000001`, jamais un hash ou une
      valeur stable dérivée d'une donnée métier.
- [ ] Les images absentes et ambiguës restent visibles dans un rapport métier
      local actionnable.
- [ ] Le rapport s'appelle `rapport-images-sensible.csv`, est encodé en UTF-8
      avec BOM et contient, dans cet ordre : `reference_technique`, `statut`,
      `id_dossier`, `nom_source`, `nom_final`, `candidats`, `action`.
- [ ] Il contient, dans l'ordre de traitement, une ligne par dossier
      `missing`, `ambiguous` ou `conversion_failed`, et seulement ces statuts.
      Sans anomalie, le fichier existe avec son seul en-tête.
- [ ] `candidats` est un tableau JSON compact de noms triés selon leur chaîne
      Unicode exacte et vaut `[]` hors ambiguïté. `action` vaut respectivement
      `provide_source`, `select_candidate` ou `replace_or_convert_source`.
- [ ] Le CSV sensible utilise la virgule, LF et les guillemets CSV standards ;
      `nom_source` peut être vide lorsqu'aucune source n'est sélectionnée.
- [ ] Le rapport reste sous le dossier de sortie ignoré par Git, porte le mode
      `0600` dès sa création atomique sur POSIX et n'est inclus dans aucun log,
      résumé, archive ou package.
- [ ] Le rapport suit la rétention du dossier de sortie, n'a pas de copie
      secondaire et fait partie des sorties connues supprimées par `--clean`.
- [ ] `run-2026-summary.json` expose seulement les compteurs traités, absents,
      ambigus et en erreur ; `images-processing-*.log` utilise seulement les
      codes, compteurs et références techniques.
- [ ] Console, stderr et journaux persistants réduisent les exceptions à leur
      classe et à un code stable, sans chemin, nom ni valeur brute.
- [ ] Des tests avec sentinelles synthétiques prouvent leur absence du journal
      technique et leur présence uniquement sur la surface métier autorisée.
- [ ] Le comportement non bloquant des images absentes reste inchangé.
- [ ] La documentation distingue clairement journal technique et rapport
      métier sensible.

## Hors périmètre

- Supprimer toutes les informations actionnables pour l'opérateur.
- Changer les règles de matching ou de conversion.
- Modifier les rapports du parcours web sans preuve d'une fuite équivalente.
- Conserver un hash stable ou non salé d'un identifiant métier.
- Publier ou inspecter un journal réel.

## Preuve attendue

- tests ciblés du traitement image scripté avec identifiants et noms sentinelles ;
- recherche automatisée des sentinelles dans le log technique et le résumé ;
- contrôle séparé de leur présence autorisée dans le rapport sensible ;
- contrôle des compteurs et du statut non bloquant ;
- commandes Ruff du dépôt ;
- `git diff --check`.

## Sources locales

- `AGENTS.md`
- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-exploitation-purge-sircom-2026.md`
- `re-run-old-script-2026/README.md`
- `re-run-old-script-2026/11-process-images.py`
- `re-run-old-script-2026/run_jeu_test_2026.py`
