---
type: Concept
title: "Sources locales de la documentation Sircom 2026"
description: "Liste des sources qui fondent la documentation PDD OKF de la voie scriptée."
tags: [pdd, okf, sources, sircom-2026]
timestamp: "2026-07-23"
sources:
  - "../variables.md"
  - "../run_jeu_test_2026.py"
  - "../sircom2026_rules.py"
  - "../sircom2026_image_matching.py"
  - "../sircom2026_image_mapping.py"
  - "../sircom2026_image_processing.py"
  - "../tests/test_image_modules.py"
  - "../13-verify_data_integrity.py"
  - "../livrables_output_2026-07-24/run-2026-summary.json"
---

# Sources

## Sources de comportement

- `../variables.md` : configuration unique des chemins, sorties, règles CSV,
  tri et images.
- `../run_jeu_test_2026.py` : orchestration, dossier de sortie daté,
  nettoyage et transmission des variables aux scripts.
- `../sircom2026_rules.py` : règles communes 2026 utilisées par plusieurs
  scripts.
- `../00-extract_departement_to_sircom.py` : extraction de l'onglet utile et
  traitement des lignes masquées.
- `../03-image_id_adder.py` : ajout de `imageid`.
- `../04-fusion_tri_region_departement.py` : tri région puis département.
- `../08-add_pathimg_excel.py` : ajout de `@pathimg`.
- `../09-optimize_content_excel.py` : nettoyage des cellules et lignes.
- `../10-export_csv_utf16_final.py` : export CSV UTF-16.
- `../11-process-images.py` : orchestration CLI du traitement images.
- `../sircom2026_image_mapping.py` : lecture du mapping Excel ID/image.
- `../sircom2026_image_matching.py` : rapprochement des noms d'images.
- `../sircom2026_image_processing.py` : conversion et redimensionnement JPEG.
- `../12-create_mapping_excel.py` : mapping neutre des colonnes.
- `../13-verify_data_integrity.py` : contrôle final des associations.
- `../tests/test_image_modules.py` : tests unitaires des modules images.

## Sources de preuve

- `../livrables_output_2026-07-24/run-2026-summary.json` : résumé du dernier
  run vérifié.
- `../livrables_output_2026-07-24/10-final-sircom-indesign-utf16.csv` : CSV
  final contrôlé.
- `../livrables_output_2026-07-24/11-export-images-id-dossier-rename-resize/` :
  images JPG produites.
- `.pdd/inventory.json` : inventaire local des sources.
- `.pdd/review/` : reçus de couverture, ancrage et régression.

## Limite

La documentation prouve la chaîne scriptée sur le jeu de test du 23 juillet
2026, avec un dernier dossier de preuve daté `2026-07-24`. Elle ne prouve pas
un import réel dans InDesign.
