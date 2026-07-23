# Voie scriptée Sircom 2026

Ce dossier contient la copie adaptée des anciens scripts Sircom pour fournir une
alternative hors interface web au parcours `sircom2026/`.

La chaîne historique `scripts-2025/` ne doit pas être modifiée pour ce besoin.

## Usage rapide

Depuis la racine du dépôt :

```bash
.venv/bin/python re-run-old-script-2026/run_jeu_test_2026.py --clean
```

Avant de relancer sur un autre lot, modifier seulement :

```text
re-run-old-script-2026/variables.md
```

Ce fichier centralise les sources, le dossier de sortie, le suffixe date,
`@pathimg`, le marqueur `#N/A`, le tri, les images et les noms de livrables.

Par défaut, `variables.md` pointe vers :

```text
livrables-miweb/livrables-2026/jeux-test-23-juillet/excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx
livrables-miweb/livrables-2026/jeux-test-23-juillet/images-jeux-test-2026.zip
```

La racine `@pathimg` par défaut est :

```text
Macintosh HD:Users:victoria:Documents:export-jpg-resize
```

Elle peut être remplacée avec :

```bash
.venv/bin/python re-run-old-script-2026/run_jeu_test_2026.py \
  --pathimg-root "Macintosh HD:Exports:sircom"
```

Les livrables sont écrits par défaut dans :

```text
re-run-old-script-2026/livrables_output_YYYY-MM-DD/
```

Exemple pour le 23 juillet 2026 :

```text
re-run-old-script-2026/livrables_output_2026-07-23/
```

Le suffixe est au format ISO court `YYYY-MM-DD`. Le dossier peut être remplacé
dans `variables.md` avec `output_dir`, ou ponctuellement avec `--output-dir`.
Avec `--clean`, le runner nettoie les artefacts générés connus dans le dossier
de sortie courant et les anciens artefacts connus qui auraient été produits à
la racine du dossier de reprise.

## Sorties utiles

- `livrables_output_YYYY-MM-DD/10-final-sircom-indesign-utf16.csv` : CSV final UTF-16
  pour InDesign.
- `livrables_output_YYYY-MM-DD/11-export-images-id-dossier-rename-resize/` : images JPG
  traitées.
- `livrables_output_YYYY-MM-DD/12-mapping-colonnes-sircom-2026.xlsx` et `.csv` :
  mapping Excel vers CSV.
- `livrables_output_YYYY-MM-DD/run-2026-summary.json` : résumé de l'exécution.
- `livrables_output_YYYY-MM-DD/images-processing-*.log` : journal du traitement
  images.

## Règles métier principales

- Onglet source : `BDD TT + ANALYSE DGDDI`.
- Lignes masquées ignorées à l'extraction.
- Identifiant métier : `Dossier ID`.
- `imageid` : `{id_dossier_normalise}.jpg`, sans préfixe `dossier-`.
- `@pathimg` : racine InDesign + `imageid`, avec séparateur adapté au chemin.
- Cellules métier vides : `#N/A`.
- Lignes totalement vides ou sans `Dossier ID` : supprimées.
- Tri : région puis département du site de production.
- Images absentes : alerte non bloquante si au moins une image est traitée.

## Documentation progressive

- [Variables de run](variables.md)
- [Spécification fonctionnelle](docs/specification-fonctionnelle.md)
- [Spécification technique](docs/specification-technique.md)
- [Vérification script par script](docs/verification-scripts-2026.md)

## Preuve du dernier run

Le dernier run complet contrôlé dans `livrables_output_2026-07-24/` a produit :

- 561 lignes CSV ;
- 20 colonnes ;
- 392 cellules `#N/A` ;
- 0 cellule vide dans les lignes exportées ;
- 0 inversion de tri région/département ;
- 10 images JPG traitées ;
- 5 tests unitaires passés sur les modules images extraits de
  `11-process-images.py`.
