---
type: Concept
title: "Vérification script par script de la voie Sircom 2026"
description: "Revue synthétique de l'utilité, de la cohérence et des preuves de chaque script."
tags: [pdd, okf, sircom-2026, verification]
timestamp: "2026-07-23"
sources:
  - "../variables.md"
  - "../run_jeu_test_2026.py"
  - "../sircom2026_rules.py"
  - "../sircom2026_image_matching.py"
  - "../sircom2026_image_mapping.py"
  - "../sircom2026_image_processing.py"
  - "../tests/test_image_modules.py"
  - "../livrables_output_2026-07-24/run-2026-summary.json"
  - "../livrables_output_2026-07-24/10-final-sircom-indesign-utf16.csv"
---

# Vérification script par script

## Position PDD

Cette page répond à la question : quels scripts sont utiles, cohérents et
vérifiés ? Pour comprendre le pipeline avant la revue, lire la
[spécification technique](specification-technique.md).

## Verdict

La chaîne `re-run-old-script-2026/` est cohérente et exécutable sur le jeu de
test officiel. Les scripts historiques restent dans `scripts-2025/` et ne sont
pas modifiés. Les livrables courants sortent dans
`livrables_output_YYYY-MM-DD/`. La configuration de run est centralisée dans
`variables.md`.

## Revue des fichiers

| Script | Rôle | Verdict |
| --- | --- | --- |
| `variables.md` | Configuration de run | Utile ; évite d'éditer les scripts pour changer de lot. |
| `sircom2026_rules.py` | Règles partagées 2026 | Utile ; évite la duplication de normalisation. |
| `run_jeu_test_2026.py` | Orchestration du jeu officiel | Utile ; rend le run reproductible. |
| `00-extract_departement_to_sircom.py` | Extraction de l'onglet source | Cohérent ; ignore les lignes masquées. |
| `01-si-cellule-vide-na.py` | Remplacement des vides | Cohérent ; applique `#N/A` pour InDesign. |
| `02-header_lettres_colonne.py` | Préfixe lettre Excel | Cohérent ; conserve la logique historique. |
| `03-image_id_adder.py` | Ajout `imageid` | Corrigé ; détecte `Dossier ID` et produit `{id}.jpg`. |
| `04-fusion_tri_region_departement.py` | Tri | Corrigé ; évite les colonnes de code postal. |
| `05-changer-date-format.py` | Dates | Cohérent ; neutre si aucune colonne date. |
| `06-livrable-final.py` | Copie livrable Excel | Utile comme point intermédiaire. |
| `07-clean_headers_excel.py` | En-têtes CSV | Corrigé ; préserve `id_dossier`, `imageid`, `@pathimg`. |
| `08-add_pathimg_excel.py` | Ajout `@pathimg` | Corrigé ; chemin Macintosh configurable. |
| `09-optimize_content_excel.py` | Nettoyage contenu | Cohérent ; conserve `#N/A`, retire les lignes invalides. |
| `10-export_csv_utf16_final.py` | Export CSV | Corrigé ; ne dépend plus de `pandas`. |
| `11-process-images.py` | Images | Refactoré ; reste l'orchestrateur CLI du traitement images. |
| `sircom2026_image_mapping.py` | Mapping image | Utile ; isole la lecture Excel ID/image. |
| `sircom2026_image_matching.py` | Rapprochement image | Utile ; isole les règles de correspondance et d'ambiguïté. |
| `sircom2026_image_processing.py` | Conversion image | Utile ; isole la conversion JPEG et le redimensionnement. |
| `tests/test_image_modules.py` | Tests image | Utile ; couvre les modules extraits du script image. |
| `12-create_mapping_excel.py` | Mapping | Corrigé ; ne dépend plus de `pandas` et produit des fichiers neutres. |
| `13-verify_data_integrity.py` | Vérification finale | Corrigé ; vérifie sans `pandas`. |

## Points de vigilance

- La réserve de conception sur `11-process-images.py` est levée : le script
  garde la CLI historique, et la logique testable vit dans trois modules locaux.
- Les images absentes sont nombreuses dans le jeu officiel, car le ZIP de test
  contient 10 images pour 561 lignes. Ce comportement est accepté par
  `--allow-missing`.
- Le mapping utilise des libellés neutres `Champ attendu` et des fichiers
  `12-mapping-colonnes-sircom-2026.*`.

## Preuves du dernier run

- Analyse syntaxique AST : 20 fichiers Python valides.
- `uv run --frozen --extra test ruff check re-run-old-script-2026` : succès.
- `uv run --frozen --extra test ruff format --check re-run-old-script-2026` :
  succès.
- `uv run --frozen --extra test pytest -p no:cacheprovider
  re-run-old-script-2026/tests/test_image_modules.py` : 5 tests passés.
- Runner : `.venv/bin/python re-run-old-script-2026/run_jeu_test_2026.py --clean`.
- Sorties contrôlées : `re-run-old-script-2026/livrables_output_2026-07-24/`.
- Vérification finale : 561 associations image/dossier conformes.
- Contrôle tri : 0 inversion région/département.
- Contrôle CSV : 0 cellule vide et 392 cellules `#N/A`.
- Contrôle images : 10 images JPEG RGB, largeur maximale inférieure ou égale à
  350 px.

## Sources

- `../variables.md` : configuration unique du dernier run.
- `../run_jeu_test_2026.py` : exécution de bout en bout.
- `../sircom2026_rules.py` : règles communes vérifiées par plusieurs scripts.
- `../sircom2026_image_mapping.py` : lecture du mapping images.
- `../sircom2026_image_matching.py` : rapprochement des noms images.
- `../sircom2026_image_processing.py` : production des JPEG.
- `../tests/test_image_modules.py` : tests unitaires des modules images.
- `../livrables_output_2026-07-24/run-2026-summary.json` : résumé du dernier
  run.
- `../livrables_output_2026-07-24/10-final-sircom-indesign-utf16.csv` : CSV
  contrôlé.
