# 03 - Bornes images pixels et conversion

Statut : `done`

Dépend de : 01.

À construire : une image source hors limites pixels, largeur ou hauteur est
signalée avant transposition, conversion RGB, redimensionnement et encodage JPEG.

## Contexte

Le pipeline images 2026 vérifie déjà le zip, les extensions, les doublons, les
chemins dangereux et la taille en octets. La conversion finale ouvre l'image,
applique l'orientation EXIF, gère l'alpha, conserve ICC et produit un JPEG 350 px
max. La limite manquante porte sur les pixels source avant traitement complet.

## Critères d'acceptation

- [x] Une image dont `width * height`, largeur ou hauteur dépasse la limite
      configurée est refusée avant `ImageOps.exif_transpose` et conversion RGB.
- [x] Le refus produit un code stable, par exemple
      `SIRCOM_IMAGE_DIMENSIONS_EXCEEDED`, avec détails non sensibles.
- [x] L'inspection zip est le point propriétaire du signalement dimensionnel ;
      le matching revalide défensivement avant conversion pour éviter une
      conversion tardive non bornée.
- [x] La limite applicative est cohérente avec `Image.MAX_IMAGE_PIXELS`. Si l'état
      global Pillow est ajusté en test ou au démarrage, il est isolé et remis en
      état pour éviter les effets de bord entre tests.
- [x] Une image valide proche des limites reste acceptée.
- [x] La sortie des images valides reste inchangée : JPEG, largeur max 350 px,
      qualité 100, DPI 300, fond blanc si alpha, orientation EXIF appliquée,
      ICC conservé si présent.
- [x] Les tests couvrent image trop large, trop haute, trop de pixels, image
      valide proche de la limite et conversion existante non régressée.
- [x] Les tests adversariaux abaissent les limites de configuration pour rester
      rapides ; ils ne créent pas de vraies images géantes.
- [x] Une image déclenchant `PIL.Image.DecompressionBombError` est convertie en
      blocage métier `SIRCOM_IMAGE_DIMENSIONS_EXCEEDED`, pas en échec technique
      du worker.
- [x] Les limites globales du zip sont évaluées avant les ouvertures Pillow si
      le zip est déjà invalide par nombre de fichiers, nombre d'images ou volume
      décompressé.

## Hors périmètre

- Support HEIC/HEIF.
- Annulation effective pendant la boucle de conversion.
- Changement du nom `export-jpg-resize/`.
- Changement du chemin final InDesign.

## Preuve attendue

- Tests ciblés inspection ou matching images.
- Test de non-régression sur la conversion JPEG existante.
- `uv run --frozen --extra test ruff check .`

## Clôture post-ShipGuard

Commit complémentaire : `027dfad` -
`Handle Pillow image bombs as business blockers`.

Preuves exécutées :

- test rouge observé avant correction : PNG synthétique minuscule avec
  dimensions déclarées extrêmes faisait échouer le worker ;
- `uv run --frozen --extra test python -m unittest tests.test_image_upload.ImageZipInspectionPipelineTest.test_worker_blocks_pillow_image_bomb_as_dimension_problem` :
  OK ;
- `uv run --frozen --extra test python -m unittest tests.test_image_matching.ImageMatchingRulesTest.test_processed_zip_marks_pillow_image_bomb_as_dimension_failure` :
  OK ;
- `uv run --frozen --extra test python -m unittest tests.test_image_upload.ImageZipInspectionPipelineTest.test_zip_count_limit_blocks_before_pillow_opens_images` :
  OK ;
- `uv run --frozen --extra test python -m unittest tests.test_image_upload tests.test_image_matching` :
  34 tests OK ;
- CI GitHub `30010934717` verte.

## Sources locales

- `sircom2026/images.py`
- `sircom2026/image_formats.py`
- `sircom2026/image_matching.py`
- `tests/`
- `docs/audits/2026-07-23-contre-revue-glm.md`
