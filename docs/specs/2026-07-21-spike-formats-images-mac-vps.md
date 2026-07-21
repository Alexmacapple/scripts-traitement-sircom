# Spike formats images Mac/VPS - Sircom 2026

Date : 2026-07-21.

## Environnement local testé

- Python : `3.14.6`
- Pillow : `12.3.0`
- Exécutable : `.venv/bin/python`

Support Pillow observé localement :

| Fonction | Résultat | Version observée |
|---|---|---|
| JPEG / libjpeg-turbo | supporté | `libjpeg_turbo 3.1.4.1`, codec `jpg 6.2` |
| PNG / zlib | supporté | `zlib 1.3.1.zlib-ng`, `zlib_ng 2.3.3` |
| WEBP | supporté | `1.6.0` |
| TIFF / libtiff | supporté | `4.7.1` |
| LittleCMS2 / profils couleur | supporté | `2.19` |
| HEIC / HEIF | non enregistré | aucune extension `.heic` ou `.heif` enregistrée |

## Décision V1

Formats sources acceptés pour le traitement images V1 :

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`
- `.tif`
- `.tiff`

HEIC et HEIF sont refusés explicitement en V1. Aucun traitement final ne doit
dépendre d'un support HEIC implicite dans Pillow ou macOS. Si le Sircom veut
accepter HEIC ensuite, il faudra un ticket dédié avec dépendance explicite
(`pillow-heif` ou équivalent), smoke test Mac et smoke test VPS.

## Écart VPS à surveiller

Le déploiement VPS devra installer les dépendances Python du projet, dont
`Pillow>=12,<13`, puis lancer le smoke test `tests.test_image_formats`. La V1 ne
requiert pas de bibliothèque système HEIC/libheif.

Les wheels Pillow locales exposées par le smoke test incluent JPEG, PNG, WEBP,
TIFF et LittleCMS2. Si une image de base VPS recompile Pillow depuis les sources,
elle devra fournir les bibliothèques système équivalentes, sinon le smoke test
doit échouer avant ouverture du traitement images.

## Preuve

Commandes exécutées :

```bash
.venv/bin/python -m unittest tests.test_image_formats
.venv/bin/python -m unittest tests.test_image_formats tests.test_image_upload
.venv/bin/python -c "from sircom2026.image_formats import pillow_support_report; import json; print(json.dumps(pillow_support_report(), ensure_ascii=False, sort_keys=True, indent=2))"
```

Résultat local : smoke tests verts ; rapport Pillow avec JPEG, PNG, WEBP, TIFF
et LittleCMS2 supportés, HEIC/HEIF absents de `Image.registered_extensions()`.
