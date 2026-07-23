---
type: Concept
title: "Spécification technique de la voie scriptée Sircom 2026"
description: "Architecture, pipeline et contrôles techniques des scripts 2026."
tags: [pdd, okf, sircom-2026, specification-technique]
timestamp: "2026-07-23"
sources:
  - "../variables.md"
  - "../run_jeu_test_2026.py"
  - "../sircom2026_rules.py"
  - "../sircom2026_image_matching.py"
  - "../sircom2026_image_mapping.py"
  - "../sircom2026_image_processing.py"
  - "../00-extract_departement_to_sircom.py"
  - "../11-process-images.py"
  - "../13-verify_data_integrity.py"
---

# Spécification technique

## Position PDD

Cette page répond à la question : comment la voie scriptée 2026 produit-elle les
livrables ? Pour le contrat métier, lire d'abord la
[spécification fonctionnelle](specification-fonctionnelle.md).

## Architecture

La voie scriptée reste une chaîne séquentielle de fichiers numérotés. Le runner
`run_jeu_test_2026.py` orchestre la chaîne et lit `../variables.md`. Les scripts
sont appelés depuis leur dossier source, mais leur
répertoire courant est le dossier daté `livrables_output_YYYY-MM-DD/`, afin de
séparer le code des artefacts.

Le module `sircom2026_rules.py` centralise la lecture des variables et les
règles partagées :

- détection de `Dossier ID` ;
- normalisation `imageid` ;
- construction `@pathimg` ;
- nettoyage des en-têtes CSV ;
- détection des valeurs vides.

Le runner transmet les variables aux scripts via `SIRCOM_*`, afin que les
scripts restent exécutables seuls tout en partageant le même contrat.

Le traitement images est séparé en quatre fichiers :

- `11-process-images.py` : interface CLI et orchestration du traitement ;
- `sircom2026_image_mapping.py` : lecture du mapping Excel ID/image ;
- `sircom2026_image_matching.py` : rapprochement des noms d'images ;
- `sircom2026_image_processing.py` : conversion, redimensionnement et écriture
  JPEG.

## Pipeline

1. `00-extract_departement_to_sircom.py` extrait l'onglet utile et ignore les
   lignes masquées.
2. `01-si-cellule-vide-na.py` remplace les cellules vides par `#N/A`.
3. `02-header_lettres_colonne.py` préfixe les en-têtes par leur lettre Excel.
4. `03-image_id_adder.py` insère `imageid` après `Dossier ID`.
5. `04-fusion_tri_region_departement.py` trie région puis département.
6. `05-changer-date-format.py` formate les colonnes date si présentes.
7. `06-livrable-final.py` produit le livrable Excel intermédiaire.
8. `07-clean_headers_excel.py` nettoie les en-têtes InDesign.
9. `08-add_pathimg_excel.py` insère `@pathimg`.
10. `09-optimize_content_excel.py` nettoie le contenu et retire les lignes ou
    colonnes invalides.
11. `10-export_csv_utf16_final.py` exporte le CSV UTF-16.
12. `11-process-images.py` orchestre le traitement des images.
13. `12-create_mapping_excel.py` produit le mapping.
14. `13-verify_data_integrity.py` vérifie les associations ID, image et CSV.

## Tri région/département

Le tri détecte les en-têtes normalisés contenant `region` et `departement`.
Une colonne contenant `postal` n'est jamais utilisée comme département.

La clé de tri est :

```text
region.casefold(), code_departement_numerique_si_present, libelle_departement
```

## Dépendances

La chaîne utilise l'environnement applicatif `.venv` :

- `openpyxl` pour Excel ;
- `Pillow` pour les images ;
- bibliothèque standard pour CSV, ZIP, JSON, logs et chemins.

`pandas` n'est pas requis.

## Artefacts générés

Le runner peut nettoyer uniquement les artefacts connus avec `--clean`. Les
scripts restent en place. Le nettoyage retire aussi les anciens artefacts connus
qui auraient été produits à la racine de `re-run-old-script-2026/`.
Les noms d'artefacts configurés dans `../variables.md` doivent rester des
chemins relatifs bornés, sans chemin absolu, sans `..` et sans `.` comme cible.

Artefacts principaux :

- `livrables_output_YYYY-MM-DD/00-sircom-source.xlsx` à
  `09-optimize-content.xlsx` ;
- `livrables_output_YYYY-MM-DD/10-final-sircom-indesign-utf16.csv` ;
- `livrables_output_YYYY-MM-DD/images/` ;
- `livrables_output_YYYY-MM-DD/11-export-images-id-dossier-rename-resize/` ;
- `livrables_output_YYYY-MM-DD/12-mapping-colonnes-sircom-2026.*` ;
- `livrables_output_YYYY-MM-DD/run-2026-summary.json`.

Les noms de ces artefacts sont configurables dans `../variables.md`.

## Contrôles ZIP et images

Le ZIP images de la voie scriptée est volontairement plat : les images utiles
doivent être à la racine du ZIP. Les fichiers système macOS (`__MACOSX/` et
fichiers cachés) sont ignorés. Les autres sous-dossiers et les doublons de nom
après normalisation de casse sont refusés avant extraction.

Les formats source acceptés sont ceux du contrat applicatif local : JPEG, PNG,
WEBP et TIFF. Avant conversion, chaque image source est bornée par :

- `image_source_max_pixels` ;
- `image_source_max_width_px` ;
- `image_source_max_height_px`.

Le traitement image ne désactive pas la protection globale `Image.MAX_IMAGE_PIXELS`
de Pillow. Les images produites restent des JPEG de largeur maximale
`image_max_width_px`.

## Contrôles techniques

- Analyse syntaxique AST de tous les scripts.
- Exécution complète du runner.
- Tests unitaires ciblés des modules image.
- Contrôle indépendant du CSV :
  - 561 lignes ;
  - 20 colonnes ;
  - 0 cellule vide ;
  - 392 cellules `#N/A` ;
  - 0 erreur `imageid` ;
  - 0 erreur de préfixe `@pathimg` ;
  - 0 inversion de tri.
- Contrôle indépendant des images :
  - 10 images produites ;
  - 0 image non JPEG, non RGB ou supérieure à 350 px.

## Sources

- `../variables.md` : configuration unique appliquée au pipeline.
- `../run_jeu_test_2026.py` : orchestration, dossier de sortie et nettoyage.
- `../sircom2026_rules.py` : règles partagées.
- `../11-process-images.py` : orchestration CLI du traitement images.
- `../sircom2026_image_mapping.py` : mapping Excel vers images sources.
- `../sircom2026_image_matching.py` : rapprochement strict des noms de fichiers.
- `../sircom2026_image_processing.py` : conversion et redimensionnement JPEG.
- `../00-extract_departement_to_sircom.py` : extraction de l'onglet source et
  exclusion des lignes masquées.
- `../13-verify_data_integrity.py` : vérification finale ID, image et CSV.
