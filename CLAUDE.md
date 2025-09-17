# CLAUDE.md

Ce fichier fournit des instructions à Claude Code (claude.ai/code) pour travailler avec le code de ce dépôt.

## Vue d'ensemble du projet

Il s'agit d'une chaîne de traitement de données pour le catalogue de la Grande Exposition du Fabriqué en France 2025. Elle transforme les exports Excel de la plateforme "Démarches Simplifiées" en fichiers prêts pour InDesign.

## 🆕 Structure mise à jour (Septembre 2025)

La structure Excel a été modifiée :
- **Ancienne structure** : ~95 colonnes (A-CQ)
- **Nouvelle structure** : 25 colonnes (A-Y)
- Les colonnes clés ont été repositionnées (ID en F, Entreprise en H, Produit en G)
- Un nouveau champ "Label IG" a été ajouté en colonne O
- Le champ "Ville de production" a été supprimé

## Fichiers requis et configuration

Avant de lancer la chaîne, vérifier la présence de ces fichiers :
- `Sircom.xlsx` - Export Excel depuis Démarches Simplifiées avec 25 colonnes (nom obligatoire)
- `images/` - Dossier contenant les images des produits (anciennement export_images_id_dossier/)

## Commandes

### Chaîne de traitement complète
```bash
# Lancer la chaîne complète avec sortie détaillée
python3 sircom_master_script.py --verbose

# Lancer sans mode verbose
python3 sircom_master_script.py
```

### Exécution individuelle des scripts
Chaque script peut être exécuté indépendamment si nécessaire :
```bash
python3 0-si-cellule-vide-na.py        # Normaliser les cellules vides en #N/A
python3 1-header_lettres_colonne.py    # Ajouter les références de colonnes
python3 2-image_id_adder.py            # Générer les identifiants d'images
python3 3-fusion_tri_region_departement.py  # Tri géographique
python3 4-changer-date-format.py       # Formater les dates au format français
python3 5-livrable-final.py            # Générer le livrable Excel final
python3 6-clean_headers_excel.py       # Nettoyer les en-têtes pour InDesign
python3 7-add_pathimg_excel.py         # Ajouter les chemins d'images (configurable)
python3 8-optimize_content_excel.py    # Optimiser le contenu
python3 9-export_csv_utf16_final.py    # Exporter CSV UTF-16 pour InDesign
python3 10-process-images.py           # Traiter et redimensionner les images
python3 11-create_mapping_excel.py     # Créer le mapping des colonnes
python3 12-verify_data_integrity.py    # Vérifier l'intégrité des données
```

## Architecture de la chaîne de traitement

La chaîne suit un modèle de transformation séquentiel avec 13 scripts :

1. **Normalisation des données (Scripts 0-5)** : Nettoyage Excel, standardisation et tri géographique
2. **Préparation InDesign (Scripts 6-9)** : Nettoyage des en-têtes, injection des chemins, export CSV UTF-16
3. **Traitement d'images (Script 10)** : Lit le mapping Excel (Colonne F=ID, Colonne Y=nom image), redimensionne à 350px max, maintient 300 DPI
4. **Validation (Scripts 11-12)** : Création du mapping des colonnes et vérification de l'intégrité

### Flux de données principal
- Entrée : `Sircom.xlsx` (Excel avec colonnes A à Y - nouvelle structure 25 colonnes)
- Fichiers intermédiaires : Chaque script crée des fichiers de sortie numérotés
- Sorties finales :
  - `5-livrable-final-word.xlsx` - Livrable pour les équipes métier
  - `9-final-sircom-indesign-utf16.csv` - Fichier de fusion de données InDesign
  - `export_images_id_dossier_rename_resize/` - Images optimisées

### Configuration du chemin des images
Le script 7 demande le chemin des images pour InDesign (défaut : `/Users/victoria/Documents/export-jpg-resize`). Ce chemin est écrit au format POSIX pour compatibilité InDesign 19.4+.

## Dépendances principales
- Python 3.x
- pandas
- openpyxl
- Pillow (pour le traitement d'images)

Le script maître crée automatiquement un environnement virtuel et installe les dépendances.

## Mapping des données (Nouvelle structure 25 colonnes)
- Colonne Excel F (index 5) : ID du dossier
- Colonne Excel G (index 6) : Nom du produit
- Colonne Excel H (index 7) : Nom de l'entreprise
- Colonne Excel Y (index 24) : Photo/nom du fichier image
- Colonne Excel O (index 14) : Label IG (nouveau champ)

## Gestion des erreurs
- Tous les scripts valident l'existence des fichiers d'entrée
- Sauvegardes automatiques créées avec horodatage
- Logs détaillés dans `sircom-processing-YYYYMMDD-HHMMSS.log`
- Arrêt du traitement sur erreur critique pour éviter la corruption des données

## Notes importantes
- Les scripts ont été adaptés pour la nouvelle structure 25 colonnes (septembre 2025)
- Le script de traitement d'images (10) utilise maintenant les colonnes F (ID) et Y (Photo)
- Les IDs peuvent être alphanumériques (ex: ARA07.2025-HGV) et sont normalisés en minuscules sans espaces/points pour les noms d'images
- L'encodage UTF-16 est requis pour la compatibilité InDesign 19.4+
- Tous les chemins utilisent le format POSIX pour la compatibilité multiplateforme
- Scripts 11 et 12 ajoutés pour le mapping et la vérification d'intégrité