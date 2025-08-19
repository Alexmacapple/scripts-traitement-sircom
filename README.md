# Guide d'utilisation - Traitement Sircom Made in France 2025

## 🎯 Objectif

Cette chaîne de traitement automatise la préparation des données pour le catalogue de la Grande Exposition du Fabriqué en France 2025. Elle transforme l'export Excel de Démarches Simplifiées en fichiers prêts pour InDesign.

## 📋 Prérequis

### 1. Environnement technique
- **Python 3.x** installé sur votre machine
- **macOS** (les scripts sont optimisés pour Mac)
- Environ 500 MB d'espace disque disponible

### 2. Fichiers nécessaires

#### Fichier Excel source
- **Nom obligatoire** : `Sircom.xlsx`
- **Provenance** : Export depuis la plateforme Démarches Simplifiées
- **Emplacement** : Dans le dossier `scripts-traitement-sircom/`

#### Dossier d'images
- **Nom obligatoire** : `export_images_id_dossier`
- **Contenu** : Images des produits (JPG, PNG, etc.)
- **Emplacement** : Dans le dossier `scripts-traitement-sircom/`
- **Important** : Le nombre d'images doit correspondre au nombre de dossiers valides dans le fichier Excel

## 🚀 Lancement du traitement

### Étape 1 : Préparer les fichiers

```bash
# Se placer dans le bon dossier
cd /chemin/vers/scripts-traitement-sircom/

# Vérifier la présence des fichiers
ls -la Sircom.xlsx
ls -la export_images_id_dossier/
```

### Étape 2 : Lancer le script maître

```bash
python3 sircom_master_script.py --verbose
```

### Étape 3 : Configuration du chemin des images

Le script vous demandera :
```
🖼️  Configuration du chemin des images pour InDesign
Chemin par défaut : /Users/victoria/Documents/export-jpg-resize

Appuyez sur Entrée pour garder le défaut, ou saisissez un nouveau chemin :
```

- **Pour Victoria** : Appuyez sur Entrée pour utiliser le chemin par défaut
- **Pour un autre utilisateur** : Tapez le chemin complet où seront placées les images pour InDesign

## ⏱️ Durée du traitement

Le traitement complet prend environ **30 secondes** et exécute automatiquement 12 scripts :

1. **Scripts 0-5** : Traitement Excel (normalisation, tri, formatage)
2. **Scripts 6-9** : Préparation InDesign (nettoyage, chemins d'images)
3. **Script 10** : Optimisation des images (redimensionnement, renommage)
4. **Script 11** : Création du mapping des colonnes

## 📦 Fichiers générés

### Livrables principaux

1. **`5-livrable-final-word.xlsx`**
   - Fichier Excel final pour les équipes métier
   - Données triées par région et département
   - Dates au format français

2. **`9-final-sircom-indesign-utf16.csv`**
   - Fichier CSV pour la fusion de données InDesign
   - Encodage UTF-16 compatible avec InDesign 19.4+
   - Chemins d'images au format POSIX

3. **`export_images_id_dossier_rename_resize/`**
   - Dossier contenant les images optimisées
   - Images redimensionnées à 350px max
   - Nommage : `dossier-XXXXX.jpg`

4. **`mapping_colonnes_charles.xlsx`**
   - Tableau de correspondance des colonnes
   - Indique les champs demandés par Charles
   - Aide pour le mapping dans InDesign

### Fichiers de suivi

- **`sircom-processing-YYYYMMDD-HHMMSS.log`** : Log détaillé du traitement
- **`sircom-rapport-YYYYMMDD-HHMMSS.txt`** : Rapport de synthèse

## 🔧 En cas de problème

### Le script s'arrête avec une erreur

1. Consultez le message d'erreur affiché
2. Vérifiez le fichier de log pour plus de détails
3. Causes fréquentes :
   - Fichier `Sircom.xlsx` manquant ou mal nommé
   - Dossier `export_images_id_dossier` manquant
   - Nombre d'images différent du nombre de dossiers

### Relancer après une erreur

```bash
# Les fichiers intermédiaires sont sauvegardés
# Vous pouvez relancer directement :
python3 sircom_master_script.py --verbose
```

## 📝 Structure attendue des fichiers

### Sircom.xlsx
- Export standard depuis Démarches Simplifiées
- Contient les colonnes A à CQ
- Une ligne d'en-têtes + les dossiers de candidature

### Images
- Un fichier image par dossier
- Formats acceptés : JPG, PNG, GIF, WEBP, etc.
- L'ordre alphabétique des fichiers doit correspondre à l'ordre des dossiers

## 🎨 Utilisation dans InDesign

1. **Importer le CSV** : `9-final-sircom-indesign-utf16.csv`
2. **Configurer les images** : Utiliser la colonne `@pathimg`
3. **Mapper les champs** : Se référer à `mapping_colonnes_charles.xlsx`
4. **Lancer la fusion** : InDesign créera automatiquement les pages

## 💡 Astuces

- **Mode verbose** : Utilisez `--verbose` pour voir le détail de chaque étape
- **Sauvegardes** : Le script crée automatiquement des sauvegardes datées
- **Logs** : Consultez les logs en cas de comportement inattendu

## 📞 Support

En cas de difficultés :
1. Vérifiez d'abord cette documentation
2. Consultez les logs de traitement
3. Contactez l'équipe technique avec le fichier de log

---

**Version** : 2.0 (Compatible InDesign 19.4+ avec chemins POSIX)  
**Dernière mise à jour** : Août 2025