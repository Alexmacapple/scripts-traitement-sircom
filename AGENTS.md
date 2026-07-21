# AGENTS.md - Sircom Made in France

## Mission

Ce dépôt contient l'héritage 2025 de traitement Sircom et prépare l'interface web Sircom 2026.

Objectif 2025 : transformer l'export Excel `Sircom.xlsx` de Démarches Simplifiées en fichiers prêts pour InDesign et en livrables de suivi métier.

Objectif 2026 : construire une application web qui permet au Sircom d'uploader un Excel multi-onglets, mapper les champs utiles, uploader un zip d'images, traiter les données/images et exporter un package final compatible InDesign.

## Sources de vérité locales

- `README.md` : guide utilisateur et déroulé opérationnel.
- `CLAUDE.md` : pointeur de compatibilité vers ce fichier.
- `TODO.md` : tâches à traiter et points d'implémentation à ne pas oublier.
- `CHANGELOG.md` : historique synthétique des décisions et changements.
- `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` : source de cadrage 2026 pour mapping, images, CSV, UI, risques et décisions.
- `sircom_master_script.py` : orchestration de la chaîne complète.
- `scripts-2025/` : scripts d'étapes numérotés `0-*.py` à `12-*.py` et utilitaire `0-extract_departement_to_sircom.py`.
- `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv` : référence d'output CSV InDesign 2025.
- `livrables-miweb-2025/livrables-miweb-1-2025/mapping_excel_csv.md` et `structure_csv_analysis.md` : références de mapping et structure du CSV final.

## Entrées attendues

### Chaîne 2025

- `Sircom.xlsx` à la racine du dépôt, avec la structure 25 colonnes A à Y.
- Images produits dans un répertoire de travail à définir selon le lot.

Ne pas supposer l'ancienne structure Excel à environ 95 colonnes sans demande explicite. La structure active documentée est celle de septembre 2025 :

- colonne F : ID du dossier ;
- colonne G : nom du produit ;
- colonne H : nom de l'entreprise ;
- colonne O : label IG ;
- colonne Y : photo ou nom du fichier image.

### Cible 2026

- Excel multi-onglets uploadé par l'utilisateur.
- Chaque onglet utile doit permettre d'identifier une colonne logique `id_dossier`.
- Ne pas coder en dur `B_ID`, `F_ID` ou une position de colonne : ces lettres sont des positions 2025, pas une règle métier 2026.
- Zip images uploadé par lot ; nom du zip libre ; images attendues à la racine du zip.

## Commandes utiles

Chaîne complète :

```bash
python3 sircom_master_script.py --verbose
python3 sircom_master_script.py
```

Vérification finale ciblée :

```bash
python3 scripts-2025/12-verify_data_integrity.py
```

Exécution d'une étape isolée :

```bash
python3 scripts-2025/<script-numéroté>.py
```

Le script maître peut créer un environnement virtuel et installer les dépendances nécessaires. Les dépendances principales sont `pandas`, `openpyxl` et `Pillow`.

## Sorties et artefacts

### Chaîne 2025

Sorties principales attendues après traitement :

- `5-livrable-final-word.xlsx` ;
- `9-final-sircom-indesign-utf16.csv` ;
- `export_images_id_dossier_rename_resize/` ;
- `mapping_colonnes_charles.xlsx`.

Artefacts de suivi possibles :

- `sircom-processing-YYYYMMDD-HHMMSS.log` ;
- `sircom-rapport-YYYYMMDD-HHMMSS.txt` ;
- sauvegardes horodatées.

Ne pas commiter les fichiers de données réelles, exports générés, logs, sauvegardes ou images optimisées sauf demande explicite.

### Package cible 2026

Le package final 2026 doit contenir au minimum :

- CSV final compatible InDesign, au format du CSV 2025 de référence ;
- images renommées et optimisées dans `export-jpg-resize/` ;
- rapport métier et technique ;
- mapping utilisé avec provenance complète.

## Zones sensibles

- Encodage du CSV final : UTF-16 requis pour InDesign 19.4+.
- Chemin final InDesign : la colonne `@pathimg` doit viser `/Users/victoria/Documents/export-jpg-resize` sauf consigne contraire explicite.
- Images sources 2026 : le zip uploadé est la source images du lot ; ne pas le confondre avec le chemin final InDesign.
- Identifiants images : les IDs peuvent être alphanumériques et doivent rester compatibles avec la normalisation existante.
- Ordre des scripts : la chaîne est séquentielle ; ne pas déplacer une étape hors de `scripts-2025/` sans mettre à jour l'orchestrateur et vérifier les fichiers intermédiaires consommés par les suivantes.
- Données personnelles ou métier : masquer les valeurs sensibles dans les comptes rendus et ne citer que les noms de fichiers, colonnes ou variables nécessaires.

## Règles métier 2026 verrouillées

- Fusion à plat des onglets par clé primaire logique `id_dossier`.
- Une seule colonne `id_dossier` exportée dans le CSV final ; les autres colonnes `id_dossier` servent à la fusion interne.
- Sans mapping utilisateur, toutes les colonnes de tous les onglets sont mises à plat ; avec mapping, seules les colonnes sélectionnées sont exportées.
- Import Excel : refuser l'import si la structure est ambiguë ou non fiable, notamment cellules fusionnées, en-têtes sur plusieurs lignes, colonnes masquées, formules ou impossibilité d'identifier proprement les en-têtes et `id_dossier`; afficher un message clair indiquant quoi corriger.
- Mapping interne avec provenance complète : onglet source, lettre colonne, nom original, nom CSV final, statut exporté ou supprimé.
- Renommage des colonnes selon 2025 : préfixe lettre Excel, minuscules, sans accents, sans caractères spéciaux, 10 caractères maximum.
- `imageid` et `@pathimg` sont placés juste après `id_dossier`.
- Sortie CSV finale strictement fidèle au CSV 2025 de référence : UTF-16 avec BOM, séparateur virgule, LF, guillemets automatiques si nécessaire, cellules vides conservées en sortie.
- Les absences doivent être signalées dans l'interface et le rapport, même si elles sortent en cellule vide dans le CSV.
- Colonnes entièrement vides supprimées, même si elles avaient été sélectionnées dans le mapping.
- Lignes sans `id_dossier` supprimées et signalées dans le rapport.
- Tri région puis département proposé et confirmé dans l'interface ; si les colonnes ne sont pas détectées, alerte non bloquante et ordre Excel conservé.
- Retours ligne dans les cellules convertis en `<br>` ; espaces début/fin supprimés ; espaces multiples réduits.
- Dates : si une colonne date est détectée ou confirmée dans le mapping, convertir les valeurs valides au format `dd/mm/yyyy` selon la règle 2025 ; signaler les valeurs invalides ou absentes, mais conserver des cellules vides dans le CSV final.
- Champs sensibles à préserver en texte : `id_dossier`, SIRET, téléphone, code postal, département et codes administratifs.
- Traitements lourds : zip images, conversion et génération de package doivent s'exécuter en tâche de fond avec progression visible ; ne pas faire dépendre ces traitements d'une requête HTTP bloquante.
- Images : une image principale par dossier en V1 ; absence d'image non bloquante ; images non référencées ignorées mais listées ; ambiguïtés de correspondance à résoudre manuellement.
- Images finales : JPG, largeur max 350 px, qualité JPEG 100, DPI 300, fond blanc pour transparence, orientation EXIF appliquée.
- Le dossier d'images final du package 2026 s'appelle `export-jpg-resize/`.

## Vérification minimale

Pour un changement de code :

1. relire le diff ;
2. lancer la commande la plus ciblée possible ;
3. si le flux complet est touché, lancer `python3 sircom_master_script.py --verbose` avec des entrées de test disponibles ;
4. vérifier `git status --short --branch`.

Pour un changement documentaire seul :

1. relire le diff ;
2. lancer le contrôle d'accents Markdown imposé par le workspace ;
3. vérifier `git status --short --branch`.

## Définition de fin

Une intervention est terminée quand le changement minimal demandé est présent, que la preuve observable a été produite ou que son absence est explicitée, et que les fichiers non liés à la demande n'ont pas été modifiés.
