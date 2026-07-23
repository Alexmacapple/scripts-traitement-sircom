---
type: Concept
title: "Spécification fonctionnelle de la voie scriptée Sircom 2026"
description: "Contrat métier des entrées, sorties et règles InDesign de la chaîne scriptée."
tags: [pdd, okf, sircom-2026, specification-fonctionnelle]
timestamp: "2026-07-23"
sources:
  - "../variables.md"
  - "../run_jeu_test_2026.py"
  - "../sircom2026_rules.py"
  - "../livrables_output_2026-07-24/run-2026-summary.json"
---

# Spécification fonctionnelle

## Position PDD

Cette page répond à la question : que doit produire la voie scriptée 2026 ?
Pour le détail d'implémentation, voir la
[spécification technique](specification-technique.md).

## Objectif

Fournir une voie scriptée Sircom 2026 reproductible, utilisable sans interface
web, sur le même jeu de test que l'application.

## Entrées

Les entrées sont définies dans `../variables.md`.

- Excel officiel :
  `excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx`.
- ZIP images officiel :
  `images-jeux-test-2026.zip`.
- Onglet extrait par défaut : `BDD TT + ANALYSE DGDDI`.
- Lignes masquées : ignorées.

## Sorties attendues

Toutes les sorties générées par le runner sont écrites par défaut dans un
dossier daté `re-run-old-script-2026/livrables_output_YYYY-MM-DD/`, avec un
suffixe ISO court configurable par `output_dir_name` et `output_date_format`.

- CSV UTF-16 avec BOM, séparateur virgule et fins de ligne LF.
- En-têtes initiaux : `id_dossier`, `imageid`, `@pathimg`,
  `b_regiondu`, `c_departem`.
- Images finales en JPG, largeur maximale 350 px, qualité 100, DPI 300.
- Mapping de colonnes en CSV et Excel.
- Résumé d'exécution JSON.

## Règles métier

- La clé métier est `Dossier ID`.
- `imageid` vaut `{id_dossier_normalise}.jpg`.
- `@pathimg` vaut `{racine_indesign}{separateur}{imageid}`.
- La racine par défaut est
  `Macintosh HD:Users:victoria:Documents:export-jpg-resize`.
- Les cellules métier vides des lignes conservées valent `#N/A`.
- Les lignes sans `Dossier ID` sont supprimées.
- Les colonnes entièrement vides sont supprimées après normalisation.
- Le tri est région puis département du site de production.
- Les images absentes sont listées comme alertes et ne bloquent pas le run si au
  moins une image est traitée.

## Critères d'acceptation

- Le runner sort avec le code `0`.
- Le CSV contient 561 lignes de données pour le jeu officiel.
- Le CSV ne contient aucune vraie cellule vide dans les lignes de données.
- Les colonnes `imageid` et `@pathimg` sont remplies pour chaque ligne exportée.
- Le tri région/département ne contient aucune inversion.
- Les 10 images présentes dans le ZIP officiel sont traitées.
- Aucun livrable courant n'est attendu à la racine de `re-run-old-script-2026/`
  après un run avec `--clean`.

## Sources

- `../variables.md` : sources, sorties et paramètres métier appliqués au run.
- `../run_jeu_test_2026.py` : orchestration, chemins par défaut et dossier de
  sortie daté.
- `../sircom2026_rules.py` : règles partagées de nommage et de chemin image.
- `../livrables_output_2026-07-24/run-2026-summary.json` : résumé du dernier
  run vérifié.
