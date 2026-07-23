---
type: Config
title: "Variables de la voie scriptée Sircom 2026"
description: "Fichier unique à éditer pour relancer les scripts Sircom 2026."
tags: [sircom-2026, scripts, configuration]
timestamp: "2026-07-23"
---

# Variables Sircom 2026

Ce fichier est la source de configuration de la voie scriptée. Il évite les
tableaux Markdown pour rester lisible sans scroll horizontal : modifier une
ligne `Valeur : ...`, puis relancer `run_jeu_test_2026.py`.

## Sources

### excel_source_path
Rôle : fichier Excel source.
Valeur : /Users/alex/Claude/projets-heberges/madeinfrance/livrables-miweb/livrables-2026/jeux-test-23-juillet/excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx
### images_source_path
Rôle : ZIP ou répertoire contenant les images source.
Valeur : /Users/alex/Claude/projets-heberges/madeinfrance/livrables-miweb/livrables-2026/jeux-test-23-juillet/images-jeux-test-2026.zip
### sheet_name
Rôle : onglet Excel à extraire.
Valeur : BDD TT + ANALYSE DGDDI

## Sortie

### output_dir
Rôle : dossier de sortie complet. `AUTO` utilise `output_dir_name` et le suffixe date.
Valeur : AUTO
### output_dir_name
Rôle : nom de base du dossier de sortie quand `output_dir` vaut `AUTO`.
Valeur : livrables_output
### append_date_suffix
Rôle : ajoute le suffixe date au dossier de sortie.
Valeur : true
### output_date_format
Rôle : format du suffixe date. `%Y-%m-%d` produit le format ISO court.
Valeur : %Y-%m-%d
### summary_output
Rôle : fichier JSON de résumé du run.
Valeur : run-2026-summary.json

## Excel et CSV

### include_hidden_rows
Rôle : `true` conserve les lignes masquées ; `false` les ignore.
Valeur : false
### empty_cell_marker
Rôle : valeur imposée dans les cellules métier vides pour InDesign.
Valeur : #N/A
### empty_value_tokens
Rôle : valeurs considérées comme vides par les scripts.
Valeur : #N/A,N/A,none,None,undefined
### csv_encoding
Rôle : encodage du CSV final.
Valeur : utf-16
### csv_delimiter
Rôle : séparateur du CSV final.
Valeur : ,
### csv_lineterminator
Rôle : fin de ligne du CSV final. `LF` signifie saut de ligne Unix.
Valeur : LF
### linebreak_replacement
Rôle : remplacement des retours ligne dans les cellules.
Valeur : <br>
### clean_header_max_length
Rôle : longueur maximale des en-têtes InDesign nettoyés.
Valeur : 10
### drop_empty_columns
Rôle : active la suppression des colonnes entièrement vides.
Valeur : true
### drop_empty_rows
Rôle : active la suppression des lignes entièrement vides.
Valeur : true
### drop_rows_without_dossier_id
Rôle : active la suppression des lignes sans `Dossier ID`.
Valeur : true

## Tri et dates

### sort_region_header_contains
Rôle : fragment attendu dans l'en-tête de région.
Valeur : region
### sort_departement_header_contains
Rôle : fragment attendu dans l'en-tête de département.
Valeur : departement
### sort_departement_header_excludes
Rôle : fragment exclu pour éviter de trier sur un code postal.
Valeur : postal
### date_header_contains
Rôle : fragment attendu dans les en-têtes de date.
Valeur : date
### date_output_format
Rôle : format de sortie des dates dans Excel.
Valeur : %d/%m/%Y
### date_input_formats
Rôle : formats de date acceptés en entrée.
Valeur : %Y-%m-%d,%Y-%m-%d %H:%M:%S,%d/%m/%Y,%d-%m-%Y

## Images et InDesign

### pathimg_root
Rôle : racine écrite dans `@pathimg` pour InDesign.
Valeur : Macintosh HD:Users:victoria:Documents:export-jpg-resize
### pathimg_separator
Rôle : séparateur entre la racine `@pathimg` et le fichier image. `AUTO` choisit `:` pour le chemin Victoria.
Valeur : AUTO
### imageid_column_name
Rôle : nom de colonne pour l'identifiant image final.
Valeur : imageid
### pathimg_column_name
Rôle : nom de colonne pour le chemin image InDesign.
Valeur : @pathimg
### image_filename_extension
Rôle : extension des images finales.
Valeur : jpg
### allow_missing_images
Rôle : `true` accepte le jeu de test avec seulement 10 images.
Valeur : true
### source_images_workdir
Rôle : dossier temporaire des images source dans le dossier de sortie.
Valeur : images
### processed_images_dir
Rôle : dossier des images JPG traitées.
Valeur : 11-export-images-id-dossier-rename-resize
### image_max_width_px
Rôle : largeur maximale des images produites.
Valeur : 350
### image_jpeg_quality
Rôle : qualité JPEG des images produites.
Valeur : 100
### image_dpi
Rôle : résolution DPI enregistrée dans les JPEG.
Valeur : 300
### image_allowed_extensions
Rôle : extensions d'images acceptées en entrée.
Valeur : jpg,jpeg,png,gif,webp,tif,tiff,bmp,eps,svg,ico,heic,heif,psd,raw,hdr,exr,jp2,pgm,ppm,xcf
### source_image_column_candidates
Rôle : colonnes candidates pour retrouver le nom d'image source.
Valeur : y_photodu,y_photo,photo_du_produit,photo_produit,photo,nom_image_source,image_source,source_image

## Fichiers d'étapes

### step_00_output
Rôle : Excel source extrait.
Valeur : 00-sircom-source.xlsx
### step_01_output
Rôle : Excel avec cellules vides remplies.
Valeur : 01-cellules-vide-na.xlsx
### step_02_output
Rôle : Excel avec lettres de colonnes.
Valeur : 02-header-lettres-colonne.xlsx
### step_03_output
Rôle : Excel enrichi avec `imageid`.
Valeur : 03-image-id.xlsx
### step_04_output
Rôle : Excel trié région puis département.
Valeur : 04-tri-region-departement.xlsx
### step_05_output
Rôle : Excel avec dates formatées.
Valeur : 05-dates-formattees.xlsx
### step_06_output
Rôle : livrable Excel intermédiaire.
Valeur : 06-livrable-final.xlsx
### step_07_output
Rôle : Excel avec en-têtes nettoyés.
Valeur : 07-clean-headers.xlsx
### step_08_output
Rôle : Excel enrichi avec `@pathimg`.
Valeur : 08-add-pathimg.xlsx
### step_09_output
Rôle : Excel optimisé.
Valeur : 09-optimize-content.xlsx
### step_10_output
Rôle : CSV final InDesign.
Valeur : 10-final-sircom-indesign-utf16.csv
### mapping_csv_output
Rôle : mapping CSV.
Valeur : 12-mapping-colonnes-sircom-2026.csv
### mapping_excel_output
Rôle : mapping Excel.
Valeur : 12-mapping-colonnes-sircom-2026.xlsx

## Mapping

### mapping_csv_encoding
Rôle : encodage du mapping CSV.
Valeur : utf-8-sig
### mapping_special_columns
Rôle : colonnes ajoutées au mapping même si elles ne viennent pas directement de l'Excel source.
Valeur : imageid,@pathimg
### mapping_expected_columns
Rôle : correspondance des lettres Excel avec les champs attendus dans le mapping.
Valeur : F=ID du dossier;G=Nom du produit;H=Nom de l'entreprise;I=Catégorie du produit;J=Description du produit;K=Prix départ usine;L=% de valeur ajouté en France;M=Exportation;N=Certification OFG;O=Label IG;P=Type d'entreprise;Q=Nombre de salariés;R=Chiffre d'affaires;S=Présentation de l'entreprise;U=Démarche de relocalisation;V=Label EPV;W=Programme du gouvernement;X=Le(s)quel(s);Y=Photo du produit

## Règles d'usage

- Garder `output_dir` à `AUTO` pour produire un dossier daté.
- Modifier `output_dir_name` pour changer le nom avant suffixe date.
- Mettre `append_date_suffix` à `false` pour produire un dossier non daté.
- Mettre `images_source_path` vers un répertoire si les images sont déjà décompressées.
- Mettre `allow_missing_images` à `false` seulement pour une livraison où toutes les images doivent être présentes.
