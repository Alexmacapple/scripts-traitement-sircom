# 01 - Limites ressources configurables et visibles

Statut : `done`

Dépend de : aucun, peut commencer immédiatement.

À construire : l'application expose et valide les limites de ressources qui
serviront aux refus Excel et images, sans changer encore les traitements métier.

## Contexte

La configuration actuelle borne les octets Excel, zip et images, mais pas les
dimensions Excel ni les pixels images. Les limites publiques exposent seulement
les Mo et les compteurs déjà existants.

## Critères d'acceptation

- [x] Les variables `SIRCOM_MAX_EXCEL_ROWS`, `SIRCOM_MAX_EXCEL_COLUMNS`,
      `SIRCOM_MAX_EXCEL_CELLS`, `SIRCOM_MAX_IMAGE_PIXELS`,
      `SIRCOM_MAX_IMAGE_WIDTH_PX` et `SIRCOM_MAX_IMAGE_HEIGHT_PX` sont chargées
      dans la configuration.
- [x] Les valeurs invalides ou nulles sont refusées au démarrage avec
      `ConfigError`, comme les autres variables numériques.
- [x] Les valeurs par défaut sont documentées dans le code de configuration :
      200 000 lignes, 256 colonnes, 5 000 000 cellules, 80 000 000 pixels,
      20 000 px largeur et 20 000 px hauteur.
- [x] La limite pixels applicative reste cohérente avec la protection Pillow :
      elle ne la désactive pas et ne laisse pas deux politiques contradictoires.
- [x] `public_limits()` expose les nouvelles limites dans les sections Excel et
      images.
- [x] Les tests de configuration couvrent valeurs par défaut, surcharge par
      environnement, refus d'une valeur invalide et présence dans
      `public_limits()`.

## Hors périmètre

- Refus effectif des Excel hors limites.
- Refus effectif des images hors limites.
- Modification de la CI.

## Preuve attendue

- Tests unitaires de configuration ciblés.
- `uv run --frozen --extra test ruff check .`
- `uv run --frozen --extra test pytest <tests ciblés> -q`

## Sources locales

- `sircom2026/config.py`
- `docs/specs/2026-07-23-chantier-a-bornes-ressources-sircom-2026.md`
