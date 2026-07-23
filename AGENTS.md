# Sircom Made in France - consignes Codex

Ce fichier est la consigne projet versionnée. Les dossiers `.hermes/`,
`.claude/` et `.agents/skills/` peuvent exister localement, mais ils sont
ignorés par Git et ne doivent plus être traités comme source de vérité du dépôt.
La CI GitHub reste versionnée dans `.github/workflows/ci.yml`.

## Sources à lire

- `README.md` : guide d'usage Sircom 2025/2026.
- `TODO.md` : état opérationnel et restes à faire.
- `CHANGELOG.md` : historique synthétique des changements.
- `docs/specs/` et `docs/tickets/` : contrats et tickets Sircom 2026.
- `re-run-old-script-2026/README.md` et `re-run-old-script-2026/docs/` :
  documentation de la voie scriptée 2026.

Les fichiers sous `livrables-miweb/` sont des données et livrables locaux
ignorés par Git. Les citer comme chemins de travail locaux, pas comme contenu
distribué par GitHub.

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
- Onglets utiles : `BDD TT + ANALYSE DGDDI` et `Etablissements`, sans lignes
  cachées, avec correspondance sur `Dossier ID`.

## Règles métier 2026 confirmées

- `imageid` est déterministe depuis `Dossier ID` et vaut
  `{id_dossier_normalise}.jpg` pour le jeu de test 2026, sans préfixe
  `dossier-`.
- `@pathimg` doit être renseigné dans le CSV final à partir de `imageid`.
  Racine par défaut :
  `Macintosh HD:Users:victoria:Documents:export-jpg-resize`.
- La racine `@pathimg` doit rester configurable par l'UI, l'API et la voie
  scriptée.
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
- Scripts 2026 : en cas de modification, exécuter
  `re-run-old-script-2026/run_jeu_test_2026.py --clean`, puis contrôler le CSV
  UTF-16, le tri région/département, `imageid`, `@pathimg` et les images
  produites.
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
