# Guide d'utilisation - Sircom Made in France

## Objectif du dépôt

Ce dépôt couvre trois usages complémentaires.

- Sircom 2025 : transformer l'export Excel `Sircom.xlsx` de Démarches
  Simplifiées en fichiers prêts pour InDesign et en livrables de suivi métier.
- Sircom 2026 web : uploader un Excel multi-onglets, mapper les champs utiles,
  traiter un zip d'images et exporter un package final compatible InDesign.
- Sircom 2026 script : fournir une alternative hors interface depuis
  `re-run-old-script-2026/`, copie isolée des scripts historiques adaptée au
  jeu de test 2026.

La chaîne 2025 reste la référence historique. Côté 2026, l'application web
locale est le parcours principal candidat ; la copie `re-run-old-script-2026/`
sert de voie scriptée à adapter et à faire tourner sur le même jeu de test.
Ne pas modifier `scripts-2025/` pour les besoins 2026.

## Sources locales utiles

- `AGENTS.md` : règles métier et consignes de travail du dépôt.
- `TODO.md` : tâches restantes pour Sircom 2026.
- `CHANGELOG.md` : historique synthétique des changements.
- `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` : cadrage complet de
  l'interface 2026.
- `docs/specs/` : contrat fonctionnel, orchestration et architecture cible
  Sircom 2026.
- `scripts-2025/` : scripts historiques numérotés utilisés par l'orchestrateur.
- `re-run-old-script-2026/` : copie de travail pour l'alternative scriptée 2026.
- `sircom2026/` et `scripts-2026/` : application web locale, diagnostic Excel
  et génération de classeurs synthétiques.
- `livrables-miweb/livrables-2026/jeux-test-23-juillet/` : jeu de test 2026 et
  notes de fusion associées.

## Prérequis

- Python 3.11 ou plus récent.
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

Les outils 2026 ne remplacent pas encore contractuellement la chaîne 2025, mais
le flux web local est déjà exécutable de l'import Excel au package final. La
voie scriptée 2026 doit rester une alternative reproductible, séparée de
`scripts-2025/`.

### Jeu de test officiel 2026

Le jeu de test de référence est :

```text
livrables-miweb/livrables-2026/jeux-test-23-juillet/excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx
livrables-miweb/livrables-2026/jeux-test-23-juillet/images-jeux-test-2026.zip
```

Règles associées :

- utiliser les onglets `BDD TT + ANALYSE DGDDI` et `Etablissements` ;
- ignorer les lignes cachées ;
- faire la correspondance sur `Dossier ID` ;
- trier, si validé, par région puis département du site de production ;
- générer `imageid` au format `{id_dossier_normalise}.jpg`, sans préfixe
  `dossier-` ;
- remplir `@pathimg` avec la racine par défaut
  `Macintosh HD:Users:victoria:Documents:export-jpg-resize`, configurable dans
  l'UI, l'API et les scripts.
- remplacer les cellules métier vides par `#N/A` dans le CSV final, après
  suppression des colonnes entièrement vides et des lignes sans `Dossier ID`.

### Lancer le socle web local

L'application FastAPI 2026 expose les routes de santé, la configuration visible,
l'OpenAPI, SQLite, le store d'artefacts, le worker local et une interface DSFR
pour piloter les lots, l'import Excel, le mapping, le CSV, les images, les
rapports, le package final, la suppression logique et la purge.

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
- `POST /api/lots/{lot_id}/excel`
- `GET /api/lots/{lot_id}/excel/diagnostic`
- `POST /api/lots/{lot_id}/retry`
- `DELETE /api/lots/{lot_id}`
- `GET /api/lots/{lot_id}/downloads/{artifact_id}`
- `/docs`
- `/openapi.json`

Worker local :

```bash
.venv/bin/python scripts-2026/run_worker_once.py --once
```

Cette commande crée la base SQLite et exécute une acquisition unique. Si
aucun job n'est prêt, elle sort normalement en `idle`.

### Alternative scriptée 2026

Le dossier `re-run-old-script-2026/` est la seule zone prévue pour adapter les
anciens scripts au jeu de test 2026. Il doit produire une sortie exploitable
hors interface web, sur les mêmes entrées Excel et ZIP que le parcours web.

Ne pas reporter ces adaptations dans `scripts-2025/`, sauf décision explicite
de migration du flux historique.

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
  tests.test_database tests.test_lots_api tests.test_artifacts tests.test_state \
  tests.test_worker tests.test_invalidation tests.test_excel_upload \
  tests.test_excel_diagnostic_pipeline
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
- sortie CSV fidèle au format InDesign attendu : UTF-16 avec BOM, séparateur
  virgule, LF, cellules métier vides remplacées par `#N/A` ;
- colonnes `imageid` et `@pathimg` placées juste après `id_dossier` ;
- `imageid` 2026 au format `{id_dossier_normalise}.jpg`, sans préfixe
  `dossier-` pour le jeu de test officiel ;
- `@pathimg` rempli avec une racine InDesign configurable, par défaut
  `Macintosh HD:Users:victoria:Documents:export-jpg-resize` ;
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

Version : 4.1

Dernière mise à jour : 23 juillet 2026
