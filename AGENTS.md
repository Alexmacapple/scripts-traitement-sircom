# Sircom Made in France - consignes Codex

Ce fichier est la consigne projet versionnée. Les dossiers `.hermes/`,
`.claude/` et `.agents/skills/` peuvent exister localement, mais ils sont
ignorés par Git et ne doivent plus être traités comme source de vérité du dépôt.
La CI GitHub reste versionnée dans `.github/workflows/ci.yml`.

## Harnais Loriq/Hermes local

Ce projet utilise Loriq/Hermes comme harnais local d'audit, de routage, de
validation et de capitalisation. Même si `.hermes/`, `.claude/` et
`.agents/skills/` ne sont pas versionnés, l'agent doit savoir que ce contexte
peut exister dans le poste de travail.

Marqueur de compatibilité Loriq local :
`Generated child Hermes adapter for .hermes/profile.yml`.

Quand la tâche mentionne Loriq, Hermes, un run opérateur, une lane, une
confirmation humaine ou une preuve issue du harnais, lire les fichiers locaux
pertinents s'ils existent, notamment `.hermes/profile.yml`,
`.hermes/control/`, `.hermes/memory/`, `.claude/agents/` et
`.agents/skills/`.

Ces fichiers sont un contexte opératoire local, pas des livrables GitHub. Ne pas
les ajouter, les régénérer, les supprimer ou les modifier sans demande
explicite.

## Sources à lire

- `README.md` : guide d'usage Sircom 2025/2026.
- `TODO.md` : état opérationnel et restes à faire.
- `CHANGELOG.md` : historique synthétique des changements.
- `docs/specs/README.md` : index normatif et ordre de préséance.
- `docs/tickets/README.md` : frontier active et taxonomie des statuts.
- `docs/specs/` et `docs/tickets/` : contrats et tickets Sircom 2026.
- `re-run-old-script-2026/README.md` et `re-run-old-script-2026/docs/` :
  documentation de la voie scriptée 2026.

Les fichiers sous `livrables-miweb/` sont des données et livrables locaux
ignorés par Git. Les citer comme chemins de travail locaux, pas comme contenu
distribué par GitHub.

## Ordre normatif et statuts

Pour décider quoi implémenter, appliquer cet ordre :

1. les règles de mission et de sécurité de `AGENTS.md` ;
2. l'index `docs/specs/README.md`, puis la spec courante qu'il désigne ;
3. les contrats de base non contredits par cette spec courante ;
4. le ticket actif, qui découpe le travail sans pouvoir modifier le contrat ;
5. `README.md`, `TODO.md` et `CHANGELOG.md`, qui décrivent l'usage et
   l'historique mais ne créent pas de règle métier.

Une règle plus récente ne remplace une règle ancienne que sur le périmètre
qu'elle cite explicitement. En cas de contradiction résiduelle, ne pas choisir
silencieusement : bloquer le ticket et faire corriger les Markdown.

Dans `docs/tickets/`, les statuts ont un sens unique :

- `ready-for-agent` : contrat fermé, dépendances closes, exécutable maintenant ;
- `blocked` : contrat fermé, mais au moins une dépendance reste ouverte ;
- `ready-for-human` : décision ou vérification humaine lançable maintenant ;
- `conditional` : ticket activé uniquement par la décision explicitement citée ;
- `done` : livraison terminée ; ne pas réimplémenter ;
- `historical` : preuve de cadrage ou d'exécution, jamais une frontier.

## Parcours à livrer

- Parcours principal candidat : application web `sircom2026/`, pilotée en local
  avec FastAPI, SQLite, worker, validation mapping/CSV/images et package final.
- Alternative scriptée : `re-run-old-script-2026/`, copie isolée des scripts
  historiques adaptée et vérifiée sur le jeu de test 2026.
- Zone à préserver : ne pas modifier `scripts-2025/` pour les besoins 2026 ;
  cette chaîne reste la référence historique 2025.

## Jeu de test de référence

- Excel :
  `livrables-miweb/livrables-2026/jeux-test-23-juillet/excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx`.
- Images :
  `livrables-miweb/livrables-2026/jeux-test-23-juillet/images-jeux-test-2026.zip`.
- Règles de fusion :
  `livrables-miweb/livrables-2026/jeux-test-23-juillet/explication-fusion-regles-metier-bdd-etablissements.md`.
- Onglets utiles : `BDD TT + ANALYSE DGDDI` et `Etablissements`, avec
  correspondance sur `Dossier ID`.
- Lignes masquées : le web refuse le classeur avec un diagnostic bloquant ; la
  voie scriptée les exclut de l'export.

## Règles métier 2026 confirmées

- `imageid` est déterministe depuis `Dossier ID` et vaut
  `{id_dossier_normalise}.jpg` pour le jeu de test 2026, sans préfixe
  `dossier-`.
- La racine `@pathimg` par défaut est :
  `Macintosh HD:Users:victoria:Documents:export-jpg-resize`.
- La racine `@pathimg` doit rester configurable par l'UI, l'API et la voie
  scriptée.
- Jusqu'à la décision humaine du ticket 2026-07-28-06, les deux parcours
  conservent leurs contrats propres : la voie scriptée renseigne `@pathimg`
  pour toute ligne à partir de `imageid`, même si l'image source manque ; le
  web ne le renseigne que lorsqu'une image finale existe. Les images absentes
  restent non bloquantes dans les deux parcours.
- Les cellules métier vides conservées dans des lignes exportées doivent sortir
  en `#N/A`, car InDesign ne supporte pas les cellules vides.
- Les colonnes entièrement vides restent supprimées et les lignes sans
  `Dossier ID` restent supprimées.
- Le tri candidat utilise `Région du site de production du produit candidat`
  puis `Département du site de production du produit candidat`. Ne pas utiliser
  une colonne de code postal comme département.
- Les images absentes sont des alertes non bloquantes ; elles doivent être
  visibles dans le rapport ou les logs.

## Voie scriptée 2026

- Orchestrateur : `re-run-old-script-2026/run_jeu_test_2026.py`.
- Configuration unique : `re-run-old-script-2026/variables.md`.
- Sorties : `re-run-old-script-2026/livrables_output_YYYY-MM-DD/`, ignorées par
  Git.
- Dernier run contrôlé : `livrables_output_2026-07-24/`, avec 561 lignes CSV,
  20 colonnes, 392 cellules `#N/A`, 0 cellule vide exportée, 0 inversion de tri
  région/département et 10 images JPG traitées.

## Preuves minimales attendues

- Web : exécuter les tests disponibles et, pour une validation produit, vérifier
  un lot réel Excel + ZIP jusqu'au téléchargement du package.
- Scripts 2026 : pour les tickets 2026-07-28-01 à 05, utiliser uniquement des
  fixtures synthétiques et ne pas traiter le jeu officiel. Le run
  `re-run-old-script-2026/run_jeu_test_2026.py --clean` sur données réelles est
  réservé au ticket humain 2026-07-28-07, après autorisation explicite. Il doit
  alors contrôler le CSV UTF-16, le tri région/département, `imageid`,
  `@pathimg` et les images produites.
- Git : avant commit ou push, vérifier `git status --short`, `git diff`,
  `git diff --cached`, et l'absence de données locales, backups ou artefacts
  générés suivis par Git.
- Documentation : après toute modification Markdown, lancer le contrôle
  d'accents depuis `/Users/alex/Claude`.

## Hygiène Git

Ne pas commiter sauf demande explicite ou besoin assumé :

- `livrables-miweb/` ;
- `re-run-old-script-2026/livrables_output_*/` ;
- `.hermes/`, `.claude/`, `.agents/skills/` ;
- `.DS_Store`, backups `*.bak`, exports, zips et logs de traitement.

À l'inverse, `.github/workflows/ci.yml` est un fichier projet versionné : toute
modification de CI doit être suivie, relue et committée.
