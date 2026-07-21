# Guide d'utilisation - Sircom Made in France

## Objectif du dépôt

Ce dépôt couvre deux usages complémentaires.

- Sircom 2025 : transformer l'export Excel `Sircom.xlsx` de Démarches
  Simplifiées en fichiers prêts pour InDesign et en livrables de suivi métier.
- Sircom 2026 : préparer une application web qui permettra d'uploader un Excel
  multi-onglets, mapper les champs utiles, traiter un zip d'images et exporter
  un package final compatible InDesign.

La chaîne 2025 reste le flux opérationnel disponible aujourd'hui. Côté 2026, le
socle FastAPI local est lancé : configuration, santé, politique d'accès, erreurs
API structurées, schéma SQLite et premier parcours lots avec timeline DSFR. Les
traitements Excel, images, CSV, rapports et package restent à brancher par
tickets successifs.

## Sources locales utiles

- `AGENTS.md` : règles métier et consignes de travail du dépôt.
- `TODO.md` : tâches restantes pour Sircom 2026.
- `CHANGELOG.md` : historique synthétique des changements.
- `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` : cadrage complet de
  l'interface 2026.
- `docs/specs/` : contrat fonctionnel, orchestration et architecture cible
  Sircom 2026.
- `scripts-2025/` : scripts historiques numérotés utilisés par l'orchestrateur.
- `sircom2026/` et `scripts-2026/` : application web locale, diagnostic Excel
  et génération de classeurs synthétiques.

## Prérequis

- Python 3.x.
- macOS pour le flux historique, les chemins et les usages InDesign existants.
- Environ 500 Mo d'espace disque disponible pour le flux 2025, davantage si les
  lots images sont volumineux.
- Dépendances principales : `pandas`, `openpyxl` et `Pillow`.

Le script maître 2025 peut créer un environnement virtuel local et installer les
dépendances nécessaires.

## Chaîne Sircom 2025

### Entrées attendues

Le fichier Excel source doit s'appeler `Sircom.xlsx` et être placé à la racine
du dépôt.

La structure active documentée pour septembre 2025 contient 25 colonnes, de A à
Y :

- colonne F : ID du dossier ;
- colonne G : nom du produit ;
- colonne H : nom de l'entreprise ;
- colonne O : label IG ;
- colonne Y : photo ou nom du fichier image.

Ne pas réutiliser l'ancienne structure à environ 95 colonnes sans demande
explicite.

### Images source

Le script historique de traitement images lit actuellement les images dans :

```text
/Users/alex/Desktop/Made-In-France/images
```

Les images peuvent être en JPG, PNG, GIF, WEBP ou autres formats supportés par
Pillow. Les IDs peuvent être alphanumériques et sont normalisés en minuscules,
sans espaces ni points, avec conservation des tirets.

### Lancer le traitement complet

```bash
python3 sircom_master_script.py --verbose
```

Version moins détaillée :

```bash
python3 sircom_master_script.py
```

Le traitement exécute les scripts `0` à `12` dans l'ordre depuis
`scripts-2025/`.

### Chemin final des images InDesign

Pendant l'exécution, le script demande le chemin final utilisé dans la colonne
`@pathimg`. Le chemin par défaut est :

```text
/Users/victoria/Documents/export-jpg-resize
```

Pour Victoria, conserver ce chemin par défaut. Pour un autre poste, saisir le
chemin POSIX complet du dossier où les images finales seront placées pour
InDesign.

### Étapes exécutées

1. Scripts 0 à 5 : normalisation Excel, ajout des lettres de colonnes, ID image,
   tri et formatage.
2. Scripts 6 à 9 : nettoyage des en-têtes, ajout de `@pathimg`, optimisation du
   contenu et export CSV UTF-16.
3. Script 10 : optimisation et renommage des images.
4. Script 11 : création du mapping des colonnes.
5. Script 12 : vérification finale d'intégrité.

### Sorties principales

- `5-livrable-final-word.xlsx` : fichier Excel final pour les équipes métier.
- `9-final-sircom-indesign-utf16.csv` : CSV final compatible InDesign 19.4+.
- `export_images_id_dossier_rename_resize/` : images optimisées par le flux
  2025.
- `mapping_colonnes_charles.xlsx` : tableau de correspondance des colonnes.

### Fichiers de suivi

- `sircom-processing-YYYYMMDD-HHMMSS.log` : log détaillé du traitement.
- `sircom-rapport-YYYYMMDD-HHMMSS.txt` : rapport de synthèse.
- Sauvegardes horodatées des fichiers remplacés, si nécessaire.

Ces fichiers sont des artefacts de traitement. Ne pas les commiter sauf demande
explicite.

## Vérification 2025 ciblée

Pour relancer seulement la vérification finale :

```bash
python3 scripts-2025/12-verify_data_integrity.py
```

Pour exécuter une étape isolée :

```bash
python3 scripts-2025/<script-numéroté>.py
```

## Outils Sircom 2026 disponibles

Les outils 2026 ne remplacent pas encore la chaîne 2025. Ils servent à préparer
la future interface web et à tester l'import Excel multi-onglets.

### Lancer le socle web local

Le socle FastAPI 2026 expose les routes de santé, la configuration visible,
l'OpenAPI, le schéma SQLite local et une interface DSFR minimale pour créer,
sélectionner et supprimer logiquement des lots.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[test]"
.venv/bin/python -m playwright install chromium
.venv/bin/python -m uvicorn sircom2026.app:app --host 127.0.0.1 --port 8000
```

Routes utiles :

- `GET /health`
- `GET /health/ready`
- `GET /api/config/limits`
- `POST /api/lots`
- `GET /api/lots`
- `GET /api/lots/{lot_id}`
- `DELETE /api/lots/{lot_id}`
- `/docs`
- `/openapi.json`

### Initialiser l'environnement local

```bash
python3 -m venv .venv
.venv/bin/python -m pip install openpyxl
```

### Diagnostiquer un ou plusieurs fichiers Excel

```bash
.venv/bin/python scripts-2026/diagnose_excel.py livrables-miweb-2025/Sircom2.xlsx
```

Le diagnostic retourne `0` si tous les classeurs sont importables, `1` si au
moins un classeur doit être refusé. Il expose la structure, les onglets, les
colonnes candidates `id_dossier`, les alertes et les blocages sans afficher les
valeurs métier.

### Générer des fichiers Excel synthétiques

```bash
.venv/bin/python scripts-2026/create_synthetic_excels.py
```

Les fichiers générés sont écrits dans `tests/fixtures/synthetic-excels/` et
restent ignorés par Git. Ils couvrent un cas multi-onglets valide et plusieurs
cas de refus : ID manquant, ID dupliqué, ID ambigu, cellules fusionnées, colonne
masquée, formule et en-tête multi-ligne.

### Lancer les tests ciblés

```bash
.venv/bin/python -m unittest tests.test_excel_diagnostic
.venv/bin/python -m unittest tests.test_web_socle tests.test_api_access_errors \
  tests.test_database tests.test_lots_api
SIRCOM_RUN_PLAYWRIGHT=1 .venv/bin/python -m unittest tests.test_lots_playwright
```

Quand les fichiers réels locaux sont présents, `Sircom2.xlsx` sert de cas
importable et `Sircom1.xlsx` sert de cas refusé, notamment à cause de colonnes
masquées et de formules.

## Cible fonctionnelle Sircom 2026

La cible 2026 est une application web locale puis serveur-ready, fondée sur
FastAPI, SQLite, un worker local intégré et une interface inspirée DSFR.

Règles métier verrouillées pour la V1 :

- fusion à plat des onglets par clé logique `id_dossier` ;
- aucune position de colonne 2025 codée en dur pour identifier `id_dossier` ;
- mapping utilisateur avec provenance complète : onglet, lettre colonne, nom
  original, nom CSV final et statut exporté ou supprimé ;
- sortie CSV fidèle au format InDesign 2025 : UTF-16 avec BOM, séparateur
  virgule, LF, cellules vides conservées ;
- colonnes `imageid` et `@pathimg` placées juste après `id_dossier` ;
- lignes sans `id_dossier` supprimées et signalées ;
- colonnes entièrement vides supprimées et signalées ;
- dates valides converties en `dd/mm/yyyy` quand la colonne est détectée ou
  confirmée comme date ;
- zip images libre en entrée, avec images attendues à la racine ;
- images finales en JPG, largeur maximale 350 px, qualité JPEG 100, DPI 300,
  fond blanc pour transparence et orientation EXIF appliquée ;
- dossier images du package final nommé `export-jpg-resize/` ;
- package final contenant au minimum CSV, images traitées, rapport et mapping.

## Dépannage

### Le script 2025 s'arrête avec une erreur

1. Lire le message d'erreur affiché.
2. Consulter le fichier `sircom-processing-YYYYMMDD-HHMMSS.log`.
3. Vérifier les causes fréquentes :
   - `Sircom.xlsx` absent de la racine du dépôt ;
   - dossier source images absent ;
   - dépendances Python manquantes ;
   - structure Excel différente de la structure 25 colonnes attendue.

### Relancer après correction

```bash
python3 sircom_master_script.py --verbose
```

Les fichiers intermédiaires existants peuvent être sauvegardés automatiquement
avant remplacement.

## Données et Git

Ne pas commiter les fichiers de données réelles, exports générés, logs,
sauvegardes, zips images ou images optimisées sauf demande explicite.

## Version

Version : 4.0

Dernière mise à jour : 21 juillet 2026
