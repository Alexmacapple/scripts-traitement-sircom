#!/usr/bin/env python3
# -*- coding: utf-8 -*-

### Ce script permet :

# de traiter automatiquement les images du dossier "export_images_id_dossier",
# de les redimensionner, convertir en JPG avec DPI 300,
# de les renommer selon les données du fichier CSV "9-final-sircom-indesign-utf16.csv",
# et de les sauvegarder dans le répertoire "export_images_id_dossier_rename_resize"

# python3 10-process-images.py

import csv
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from PIL import Image

# ==========================================
# CONFIGURATION
# ==========================================

# Paramètres de traitement d'images
MAX_WIDTH = 350
JPEG_QUALITY = 100
DPI = 300

# Chemins des fichiers et répertoires
CSV_FILE = "9-final-sircom-indesign-utf16.csv"
SOURCE_DIR = "export_images_id_dossier"
TARGET_DIR = "export_images_id_dossier_rename_resize"

# Extensions d'images supportées
ALLOWED_EXTENSIONS = [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'tif', 'tiff', 
    'bmp', 'eps', 'svg', 'ico', 'heic', 'heif', 'psd', 
    'raw', 'hdr', 'exr', 'jp2', 'pgm', 'ppm', 'xcf'
]

# ==========================================
# CONFIGURATION DU LOGGING
# ==========================================

def setup_logging():
    """Configure le système de logs pour le traitement d'images"""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_filename = f"images-processing-{timestamp}.log"
    
    # Configuration du logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info("🖼️  TRAITEMENT ET RENOMMAGE DES IMAGES - MADE IN FRANCE 2025")
    logger.info("="*80)
    logger.info(f"📅 Date/heure de début : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    logger.info(f"📝 Fichier de log : {log_filename}")
    
    return logger

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def check_prerequisites(logger):
    """Vérifier les prérequis"""
    logger.info("🔍 VÉRIFICATION DES PRÉREQUIS")
    
    # Vérifier le fichier CSV
    if not os.path.exists(CSV_FILE):
        logger.error(f"❌ Fichier CSV manquant : {CSV_FILE}")
        logger.error("💡 Assurez-vous d'avoir exécuté le script '9-export_csv_utf16_final.py' au préalable")
        return False
    logger.info(f"✅ Fichier CSV trouvé : {CSV_FILE}")
    
    # Vérifier le répertoire source des images
    if not os.path.exists(SOURCE_DIR):
        logger.error(f"❌ Répertoire d'images manquant : {SOURCE_DIR}")
        logger.error("💡 Veuillez créer le répertoire et y placer les images à traiter")
        return False
    logger.info(f"✅ Répertoire d'images trouvé : {SOURCE_DIR}")
    
    # Vérifier qu'il y a des images dans le répertoire
    image_files = get_available_images(SOURCE_DIR)
    if not image_files:
        logger.error(f"❌ Aucune image trouvée dans : {SOURCE_DIR}")
        logger.error(f"💡 Extensions supportées : {', '.join(ALLOWED_EXTENSIONS)}")
        return False
    logger.info(f"✅ {len(image_files)} images trouvées dans le répertoire source")
    
    return True

def read_csv_data(csv_file, logger):
    """Lit le fichier CSV et extrait les données de la colonne imageid"""
    logger.info(f"📖 Lecture du fichier CSV : {csv_file}")
    
    data = []
    
    # Essayer différents encodages
    encodings = ['utf-16', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(csv_file, 'r', encoding=encoding) as file:
                reader = csv.reader(file)
                headers = next(reader)  # Première ligne = en-têtes
                
                # Trouver l'index de la colonne imageid
                try:
                    imageid_index = headers.index('imageid')
                except ValueError:
                    logger.error("❌ Colonne 'imageid' non trouvée dans le CSV")
                    logger.info(f"📋 Colonnes disponibles : {', '.join(headers)}")
                    return []
                
                for row_num, row in enumerate(reader, start=2):
                    if len(row) > imageid_index:
                        imageid = row[imageid_index].strip()
                        if imageid and imageid != "#N/A":  # Vérifier que la valeur n'est pas vide
                            data.append({
                                'line': row_num,
                                'imageid': imageid
                            })
            
            logger.info(f"✅ Fichier CSV lu avec succès (encodage: {encoding})")
            logger.info(f"📊 {len(data)} références d'images trouvées dans le CSV")
            return data
            
        except UnicodeDecodeError:
            logger.debug(f"❌ Échec avec l'encodage {encoding}, essai suivant...")
            continue
        except Exception as e:
            logger.error(f"❌ Erreur avec l'encodage {encoding}: {e}")
            continue
    
    # Si aucun encodage ne fonctionne
    logger.error("❌ ERREUR : Impossible de lire le fichier CSV avec les encodages testés")
    logger.error(f"Encodages testés : {encodings}")
    return []

def get_available_images(source_dir):
    """Récupère la liste des images disponibles dans l'ordre alphabétique"""
    image_files = []
    
    for f in os.listdir(source_dir):
        ext = os.path.splitext(f)[1][1:].lower()
        if ext in ALLOWED_EXTENSIONS:
            image_files.append(f)
    
    return sorted(image_files)

def process_and_rename_image(image_path, new_name, target_dir, logger):
    """Traite une image (redimensionnement, conversion, DPI) et la renomme"""
    try:
        # Augmente la limite de pixels maximum pour l'image PIL
        Image.MAX_IMAGE_PIXELS = None
        
        # Ouvre l'image
        with Image.open(image_path) as im:
            # Redimensionne l'image en conservant l'homotétie
            im.thumbnail((MAX_WIDTH, MAX_WIDTH), Image.Resampling.LANCZOS)
            
            # Ajoute un fond blanc à une image avec un fond transparent
            if im.mode == 'RGBA':
                background = Image.new('RGB', im.size, (255, 255, 255))
                background.paste(im, mask=im.split()[3])
                im = background
            
            # Convertit en RGB si nécessaire
            if im.mode != 'RGB':
                im = im.convert('RGB')
            
            # Enregistre l'image traitée avec le nouveau nom
            out_path = os.path.join(target_dir, new_name)
            im.save(out_path, 'JPEG', quality=JPEG_QUALITY, dpi=(DPI, DPI))
            
            # Vérifier que le fichier a été créé
            if os.path.exists(out_path):
                file_size = os.path.getsize(out_path)
                logger.info(f"  ✅ Image traitée : {new_name} ({file_size:,} octets)")
                return True, file_size
            else:
                logger.error(f"  ❌ Fichier de sortie non créé : {new_name}")
                return False, 0
            
    except Exception as e:
        logger.error(f"  ❌ ERREUR lors du traitement : {e}")
        return False, 0

def analyze_correspondences(csv_data, available_images, logger):
    """Analyse les correspondances entre CSV et images disponibles"""
    logger.info("🔍 ANALYSE DES CORRESPONDANCES CSV ↔ IMAGES")
    
    # Extraire les noms d'images du CSV
    csv_images = [item['imageid'] for item in csv_data]
    
    # Correspondances parfaites (ordre du CSV)
    perfect_matches = []
    csv_missing = []
    
    for i, csv_item in enumerate(csv_data):
        csv_image = csv_item['imageid']
        if i < len(available_images):
            available_image = available_images[i]
            perfect_matches.append({
                'csv_line': csv_item['line'],
                'csv_name': csv_image,
                'available_image': available_image,
                'index': i
            })
        else:
            csv_missing.append({
                'csv_line': csv_item['line'],
                'csv_name': csv_image
            })
    
    # Images non utilisées
    unused_images = available_images[len(csv_data):]
    
    # Rapport d'analyse
    logger.info(f"📊 RÉSULTATS DE L'ANALYSE :")
    logger.info(f"  📄 Références CSV : {len(csv_data)}")
    logger.info(f"  🖼️  Images disponibles : {len(available_images)}")
    logger.info(f"  ✅ Correspondances possibles : {len(perfect_matches)}")
    logger.info(f"  ⚠️  Références CSV sans image : {len(csv_missing)}")
    logger.info(f"  ⚠️  Images non utilisées : {len(unused_images)}")
    
    return perfect_matches, csv_missing, unused_images

def main():
    """Fonction principale"""
    
    # Configuration du logging
    logger = setup_logging()
    
    try:
        # En-tête
        logger.info("🎨 PARAMÈTRES DE TRAITEMENT :")
        logger.info(f"  - Largeur max : {MAX_WIDTH}px")
        logger.info(f"  - Qualité JPEG : {JPEG_QUALITY}%")
        logger.info(f"  - DPI : {DPI}")
        logger.info(f"  - Source : {SOURCE_DIR}")
        logger.info(f"  - Destination : {TARGET_DIR}")
        
        # Vérifications préliminaires
        if not check_prerequisites(logger):
            logger.error("❌ Prérequis non satisfaits - Arrêt du traitement")
            return False
        
        # Lecture des données CSV
        csv_data = read_csv_data(CSV_FILE, logger)
        if not csv_data:
            logger.error("❌ Impossible de continuer sans données CSV")
            return False
        
        # Récupération des images disponibles
        available_images = get_available_images(SOURCE_DIR)
        logger.info(f"🖼️  Images disponibles dans {SOURCE_DIR} :")
        for i, img in enumerate(available_images):
            logger.info(f"  {i+1:2d}. {img}")
        
        # Analyse des correspondances
        perfect_matches, csv_missing, unused_images = analyze_correspondences(csv_data, available_images, logger)
        
        # Affichage des avertissements
        if csv_missing:
            logger.warning("⚠️  RÉFÉRENCES CSV SANS IMAGES CORRESPONDANTES :")
            for item in csv_missing:
                logger.warning(f"  ⚠️  Image référencée dans le CSV mais absente : {item['csv_name']} (ligne {item['csv_line']})")
        
        if unused_images:
            logger.warning("⚠️  IMAGES NON RÉFÉRENCÉES DANS LE CSV (ignorées) :")
            for img in unused_images:
                logger.warning(f"  ⚠️  Image présente mais non référencée dans le CSV : {img} (ignorée)")
        
        # Créer le répertoire de destination
        Path(TARGET_DIR).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Répertoire de destination : {TARGET_DIR}")
        
        # Traitement des images
        logger.info("="*80)
        logger.info("🚀 DÉBUT DU TRAITEMENT ET RENOMMAGE DES IMAGES")
        logger.info("="*80)
        
        success_count = 0
        error_count = 0
        total_size = 0
        
        for match in perfect_matches:
            csv_name = match['csv_name']
            available_image = match['available_image']
            csv_line = match['csv_line']
            index = match['index']
            
            logger.info(f"🔄 Traitement {index + 1}/{len(perfect_matches)} : {available_image} → {csv_name}")
            logger.info(f"  📍 Ligne CSV : {csv_line}")
            
            old_path = os.path.join(SOURCE_DIR, available_image)
            
            # Vérifier si le fichier source existe
            if not os.path.exists(old_path):
                logger.error(f"  ❌ ERREUR : Le fichier source '{available_image}' n'existe pas")
                error_count += 1
                continue
            
            # Vérifier si le fichier de destination existe déjà
            new_path = os.path.join(TARGET_DIR, csv_name)
            if os.path.exists(new_path):
                logger.warning(f"  ⚠️  Le fichier de destination '{csv_name}' existe déjà - écrasement")
            
            # Traiter et renommer l'image
            success, file_size = process_and_rename_image(old_path, csv_name, TARGET_DIR, logger)
            if success:
                success_count += 1
                total_size += file_size
            else:
                error_count += 1
        
        # Résumé final
        logger.info("="*80)
        logger.info("📋 RÉSUMÉ DU TRAITEMENT")
        logger.info("="*80)
        logger.info(f"✅ Images traitées avec succès : {success_count}")
        logger.info(f"❌ Erreurs de traitement : {error_count}")
        logger.info(f"📁 Répertoire de sortie : {TARGET_DIR}")
        logger.info(f"💾 Espace disque utilisé : {total_size:,} octets ({total_size/1024/1024:.2f} MB)")
        
        # Lister les fichiers dans le répertoire de destination
        if os.path.exists(TARGET_DIR):
            output_files = sorted(os.listdir(TARGET_DIR))
            logger.info(f"\n📂 FICHIERS CRÉÉS DANS {TARGET_DIR} :")
            for file in output_files:
                logger.info(f"  - {file}")
            logger.info(f"📊 Total fichiers créés : {len(output_files)}")
        
        # Déterminer le succès
        if success_count > 0 and error_count == 0:
            logger.info("🎉 TRAITEMENT TERMINÉ AVEC SUCCÈS !")
            return True
        elif success_count > 0:
            logger.warning("⚠️  TRAITEMENT TERMINÉ AVEC DES ERREURS")
            return True
        else:
            logger.error("❌ AUCUNE IMAGE N'A PU ÊTRE TRAITÉE")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur critique : {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
