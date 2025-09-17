# Guide d'utilisation - Traitement Sircom Made in France 2025

## 🎯 Objectif

Cette chaîne de traitement automatise la préparation des données pour le catalogue de la Grande Exposition du Fabriqué en France 2025. Elle transforme l'export Excel de Démarches Simplifiées en fichiers prêts pour InDesign.

## 🆕 Mise à jour importante (Septembre 2025)

La structure Excel a été modifiée :
- **Nouvelle structure** : 25 colonnes (A-Y) au lieu de ~95 colonnes
- **ID en colonne F** (anciennement B)
- **Entreprise en colonne H** (anciennement E)
- **Produit en colonne G** (anciennement AW)
- **Photo en colonne Y** (anciennement CE)
- **Nouveau champ** : Label IG en colonne O
- **Champ supprimé** : Ville de production

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
- **Nom du dossier** : `images` (anciennement `export_images_id_dossier`)
- **Contenu** : Images des produits (JPG, PNG, etc.)
- **Emplacement** : Dans le dossier parent `/Users/alex/Desktop/Made-In-France/images/`
- **Format des noms** : Les IDs peuvent être alphanumériques (ex: ARA07.2025-HGV) et doivent être normalisés en minuscules sans espaces ni points

## 🚀 Lancement du traitement

### Étape 1 : Préparer les fichiers

```bash
# Se placer dans le bon dossier
cd /chemin/vers/scripts-traitement-sircom/

# Vérifier la présence des fichiers
ls -la Sircom.xlsx
ls -la ../images/
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

Le traitement complet prend environ **30 secondes** et exécute automatiquement 13 scripts :

1. **Scripts 0-5** : Traitement Excel (normalisation, tri, formatage)
2. **Scripts 6-9** : Préparation InDesign (nettoyage, chemins d'images)
3. **Script 10** : Optimisation des images (redimensionnement, renommage avec mapping réel depuis Excel)
4. **Script 11** : Création du mapping des colonnes
5. **Script 12** : Vérification de l'intégrité des données (validation finale)

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
   - Nommage normalisé : `dossier-{id}.jpg` (minuscules, sans espaces ni points)

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
   - Dossier `images` manquant dans le dossier parent
   - Format des IDs non normalisé (doivent être en minuscules sans espaces ni points)

### Relancer après une erreur

```bash
# Les fichiers intermédiaires sont sauvegardés
# Vous pouvez relancer directement :
python3 sircom_master_script.py --verbose
```

## 📝 Structure attendue des fichiers

### Sircom.xlsx
- Export standard depuis Démarches Simplifiées
- **Nouvelle structure** : 25 colonnes (A à Y)
- Une ligne d'en-têtes + les dossiers de candidature

### Images
- Un fichier image par dossier (si disponible)
- Formats acceptés : JPG, PNG, GIF, WEBP, etc.
- **Mapping actuel** : Colonne F = ID, Colonne Y = nom de l'image
- **Normalisation** : Les IDs alphanumériques (ex: ARA07.2025-HGV) sont convertis en minuscules sans espaces ni points (ex: ara072025-hgv)

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

**Version** : 3.0 (Adaptée à la nouvelle structure 25 colonnes)
**Dernière mise à jour** : Septembre 2025