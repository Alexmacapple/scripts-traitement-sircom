# 34 - Extraire la génération du zip images traitées

Statut : `done`

Dépend de : 29A et 30.

À construire : déplacer la construction du zip `export-jpg-resize/` hors de
`sircom2026/image_matching.py`, sans changer le contrat public du matching
images ni les artefacts produits.

## Énoncé du problème

`image_matching.py` conserve encore la génération du zip d'images traitées, la
conversion JPG finale et les mutations de bindings liées à la conversion. Ce
bloc a été récemment durci contre les bombes Pillow ; il est maintenant bien
couvert, mais il garde une responsabilité technique distincte dans le module de
matching.

## Solution

Créer un module interne dédié à la construction du zip traité. Le seam public
reste `build_processed_images_zip(...)` importable depuis
`sircom2026.image_matching`, pour préserver les appelants et les tests du
contrat 29A.

## Décision de design

- Module candidat : génération du zip images traitées.
- Interface conservée : `build_processed_images_zip(source_zip_path,
  matching_payload, image_limits=...) -> bytes`.
- External seam : `sircom2026.image_matching.build_processed_images_zip`.
- Internal seam : module interne de construction du zip final, non exposé comme
  nouveau contrat métier.
- Depth attendue : cacher conversion, resizing, DPI, erreurs Pillow, erreurs zip
  et mutation contrôlée des bindings derrière une seule fonction.

## Critères d'acceptation

- [x] `build_processed_images_zip` reste importable depuis
      `sircom2026.image_matching`.
- [x] `EXPORT_IMAGES_FOLDER`, `FINAL_IMAGE_MAX_WIDTH_PX`,
      `FINAL_IMAGE_JPEG_QUALITY` et `FINAL_IMAGE_DPI` restent importables depuis
      `sircom2026.image_matching`.
- [x] Les statuts `matched` et `conversion_failed`, `pathimg`, `final_sha256`,
      `final_size_bytes`, `conversion_error` et
      `dimension_limits_exceeded` ne changent pas.
- [x] Les erreurs `DecompressionBombError` restent converties en
      `SIRCOM_IMAGE_DIMENSIONS_EXCEEDED`.
- [x] Aucun changement de règle de matching ou de résolution manuelle.
- [x] Les tests matching, package et rapports restent verts.

## Hors périmètre

- Modifier les règles de matching.
- Changer le format JPG final.
- Changer les chemins InDesign.
- Découper les résolutions manuelles ou l'orchestration worker.
- Refactoriser `api/lots.py`.

## Preuve attendue

- `uv run --frozen --extra test pytest tests/test_image_matching.py tests/test_package.py tests/test_reports.py -q` ;
- `uv run --frozen --extra test ruff check .` ;
- `uv run --frozen --extra test ruff format --check .` ;
- `git diff --check`.

## Livraison

Extraction réalisée :

- `sircom2026/processed_images.py` contient maintenant la construction du zip
  `export-jpg-resize/`, la conversion JPG finale, le redimensionnement, les
  métadonnées de sortie et la traduction des erreurs de conversion sur les
  bindings.
- `sircom2026/image_matching.py` conserve l'interface publique
  `build_processed_images_zip` par import depuis le module extrait.
- `EXPORT_IMAGES_FOLDER`, `FINAL_IMAGE_MAX_WIDTH_PX`,
  `FINAL_IMAGE_JPEG_QUALITY` et `FINAL_IMAGE_DPI` restent importables depuis
  `sircom2026.image_matching`.
- Le test qui vérifie que les images surdimensionnées ne passent pas en
  conversion patch maintenant le module interne extrait.

Résultat structurel :

- `sircom2026/image_matching.py` passe de 1171 à 1041 lignes.
- `sircom2026/processed_images.py` contient 147 lignes dédiées au zip traité.

Preuves exécutées le 2026-07-23 :

- `uv run --frozen --extra test pytest tests/test_image_matching.py tests/test_package.py tests/test_reports.py -q` :
  22 tests passés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `uv run --frozen --extra test pytest -q` : 249 tests passés, 5 sautés.
- `uv run --frozen --extra test python -c "from sircom2026.image_matching import ..."` :
  imports publics du ticket 34 présents.
- `git diff --check` : OK.
- `/Users/alex/Claude/scripts/check-accents.sh .../34-extraire-generation-zip-images-traitees.md .../README.md` :
  OK.
