#!/usr/bin/env python3

"""
Script Maître - Chaîne complète de traitement Sircom - Made in France 2025
===========================================================================

Ce script automatise l'exécution complète de la chaîne de traitement :
- Scripts 0-5 : Traitement Excel
- Scripts 6-9 : Traitement InDesign
- Script 10 : Traitement des images
- Script 11 : Création du mapping pour InDesign
- Script 12 : Vérification de l'intégrité des données

Fonctionnalités :
✓ Création automatique de l'environnement virtuel
✓ Installation des dépendances
✓ Exécution séquentielle avec validation inter-étapes
✓ Gestion des erreurs et arrêt en cas de problème
✓ Logs détaillés avec timestamp
✓ Rapport final avec statistiques
✓ Sauvegarde des fichiers existants
✓ Mode verbose optionnel

Usage:
    python3 sircom_master_script.py [--verbose]
"""

import os
import sys
import subprocess
import time
import shutil
from datetime import datetime
import argparse
import logging

# ==========================================
# CONFIGURATION
# ==========================================

# Configuration des chemins et paramètres
VENV_NAME = "venv"
SOURCE_FILE = "Sircom.xlsx"
SCRIPTS_DIR = "scripts-2025"
REQUIRED_PACKAGES = ["openpyxl", "pandas", "Pillow"]

# Configuration par défaut du chemin des images (format POSIX pour InDesign 19.4+)
DEFAULT_IMAGE_PATH = "/Users/victoria/Documents/export-jpg-resize"

# Liste des scripts à exécuter dans l'ordre
SCRIPTS_CHAIN = [
    {
        "script": "scripts-2025/0-si-cellule-vide-na.py",
        "description": "Normalisation des cellules vides",
        "output_file": "Sircom_vide_na.xlsx"
    },
    {
        "script": "scripts-2025/1-header_lettres_colonne.py",
        "description": "Ajout des références de colonnes",
        "output_file": "1-header-lettres-colonne-excel-mapping-excel.xlsx"
    },
    {
        "script": "scripts-2025/2-image_id_adder.py",
        "description": "Génération des identifiants d'images", 
        "output_file": "2-image-id-adder-excel-fusion.xlsx"
    },
    {
        "script": "scripts-2025/3-fusion_tri_region_departement.py",
        "description": "Tri géographique",
        "output_file": "3-fusion-tri-region-departement.xlsx" 
    },
    {
        "script": "scripts-2025/4-changer-date-format.py",
        "description": "Formatage des dates",
        "output_file": "4-changer-date.xlsx"
    },
    {
        "script": "scripts-2025/5-livrable-final.py",
        "description": "Livrable Excel final",
        "output_file": "5-livrable-final-word.xlsx"
    },
    {
        "script": "scripts-2025/6-clean_headers_excel.py",
        "description": "Nettoyage des en-têtes InDesign",
        "output_file": "6-clean-headers.xlsx"
    },
    {
        "script": "scripts-2025/7-add_pathimg_excel.py",
        "description": "Ajout des chemins d'images",
        "output_file": "7-add-pathimg.xlsx"
    },
    {
        "script": "scripts-2025/8-optimize_content_excel.py",
        "description": "Optimisation du contenu",
        "output_file": "8-optimize-content.xlsx"
    },
    {
        "script": "scripts-2025/9-export_csv_utf16_final.py",
        "description": "Export CSV final UTF-16",
        "output_file": "9-final-sircom-indesign-utf16.csv"
    },
    {
        "script": "scripts-2025/10-process-images.py",
        "description": "Traitement et renommage des images",
        "output_file": "export_images_id_dossier_rename_resize"
    },
    {
        "script": "scripts-2025/11-create_mapping_excel.py",
        "description": "Création du mapping pour InDesign",
        "output_file": "mapping_colonnes_charles.xlsx"
    },
    {
        "script": "scripts-2025/12-verify_data_integrity.py",
        "description": "Vérification de l'intégrité des données",
        "output_file": "validation"  # Pas de fichier physique, juste un placeholder pour validation
    }
]

# ==========================================
# CLASSE PRINCIPALE
# ==========================================

class SircomMasterProcessor:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.start_time = datetime.now()
        self.log_filename = f"sircom-processing-{self.start_time.strftime('%Y%m%d-%H%M%S')}.log"
        self.stats = {
            'scripts_executed': 0,
            'files_created': [],
            'execution_times': {},
            'file_sizes': {},
            'errors': []
        }
        
        # Configuration du logging
        self.setup_logging()
        
        # Variables de traitement
        self.image_path = DEFAULT_IMAGE_PATH
        
    def setup_logging(self):
        """Configure le système de logs"""
        # Configuration du logger
        logging.basicConfig(
            level=logging.DEBUG if self.verbose else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_filename, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("="*80)
        self.logger.info("🚀 DÉMARRAGE DU TRAITEMENT SIRCOM - MADE IN FRANCE 2025")
        self.logger.info("="*80)
        self.logger.info(f"📅 Date/heure de début : {self.start_time.strftime('%d/%m/%Y à %H:%M:%S')}")
        self.logger.info(f"📝 Fichier de log : {self.log_filename}")
        self.logger.info(f"🔧 Mode verbose : {'Activé' if self.verbose else 'Désactivé'}")

    def print_header(self):
        """Affiche l'en-tête du script"""
        print("\n" + "="*80)
        print("🎯 SCRIPT MAÎTRE - CHAÎNE DE TRAITEMENT SIRCOM")
        print("   Made in France 2025 - Traitement automatisé complet")
        print("="*80)
        print(f"📅 Démarrage : {self.start_time.strftime('%d/%m/%Y à %H:%M:%S')}")
        print(f"📝 Log : {self.log_filename}")
        print()

    def check_prerequisites(self):
        """Vérifier les prérequis"""
        self.logger.info("🔍 VÉRIFICATION DES PRÉREQUIS")
        
        # Vérifier Python 3
        python_version = sys.version_info
        if python_version.major < 3:
            self.logger.error("❌ Python 3.x requis")
            return False
        self.logger.info(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Vérifier le fichier source
        if not os.path.exists(SOURCE_FILE):
            self.logger.error(f"❌ Fichier source manquant : {SOURCE_FILE}")
            self.logger.error(f"💡 Veuillez déposer le fichier '{SOURCE_FILE}' dans le répertoire courant")
            return False
        self.logger.info(f"✅ Fichier source trouvé : {SOURCE_FILE}")
        
        # Vérifier que tous les scripts sont présents
        missing_scripts = []
        for script_info in SCRIPTS_CHAIN:
            if not os.path.exists(script_info["script"]):
                missing_scripts.append(script_info["script"])
        
        if missing_scripts:
            self.logger.error(f"❌ Scripts manquants : {', '.join(missing_scripts)}")
            return False
        self.logger.info(f"✅ Tous les scripts trouvés ({len(SCRIPTS_CHAIN)} scripts)")
        
        return True

    def configure_image_path(self):
        """Configuration interactive du chemin des images"""
        self.logger.info("🖼️  CONFIGURATION DU CHEMIN DES IMAGES")
        print(f"\n🖼️  Configuration du chemin des images pour InDesign")
        print(f"Chemin par défaut : {DEFAULT_IMAGE_PATH}")
        print()
        
        try:
            user_input = input("Appuyez sur Entrée pour garder le défaut, ou saisissez un nouveau chemin : ").strip()
            
            if user_input:
                self.image_path = user_input
                self.logger.info(f"✅ Chemin personnalisé configuré : {self.image_path}")
                print(f"✅ Chemin configuré : {self.image_path}")
            else:
                self.logger.info(f"✅ Chemin par défaut conservé : {self.image_path}")
                print(f"✅ Chemin par défaut conservé")
                
        except KeyboardInterrupt:
            self.logger.info("✅ Configuration interrompue, chemin par défaut conservé")
            print(f"\n✅ Chemin par défaut conservé : {self.image_path}")

    def setup_virtual_environment(self):
        """Créer et configurer l'environnement virtuel"""
        self.logger.info("🐍 CONFIGURATION DE L'ENVIRONNEMENT VIRTUEL")
        
        venv_path = os.path.join(os.getcwd(), VENV_NAME)
        
        # Créer l'environnement virtuel s'il n'existe pas
        if not os.path.exists(venv_path):
            self.logger.info(f"📦 Création de l'environnement virtuel : {VENV_NAME}")
            try:
                subprocess.run([sys.executable, "-m", "venv", VENV_NAME], 
                             check=True, capture_output=True, text=True)
                self.logger.info("✅ Environnement virtuel créé")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"❌ Erreur lors de la création de l'environnement virtuel : {e}")
                return False
        else:
            self.logger.info(f"✅ Environnement virtuel existant trouvé : {VENV_NAME}")

        # Déterminer le chemin vers Python dans l'environnement virtuel
        if os.name == 'nt':  # Windows
            python_venv = os.path.join(venv_path, "Scripts", "python.exe")
            pip_venv = os.path.join(venv_path, "Scripts", "pip.exe")
        else:  # Unix/Linux/macOS
            python_venv = os.path.join(venv_path, "bin", "python")
            pip_venv = os.path.join(venv_path, "bin", "pip")

        # Installer les dépendances
        self.logger.info("📚 Installation des dépendances")
        for package in REQUIRED_PACKAGES:
            try:
                self.logger.info(f"  📦 Installation de {package}...")
                result = subprocess.run([pip_venv, "install", package], 
                                      check=True, capture_output=True, text=True)
                self.logger.info(f"  ✅ {package} installé")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"  ❌ Erreur installation {package} : {e}")
                return False

        self.python_venv = python_venv
        self.logger.info("✅ Environnement virtuel prêt")
        return True

    def backup_existing_files(self):
        """Sauvegarder les fichiers existants avec timestamp"""
        self.logger.info("💾 SAUVEGARDE DES FICHIERS EXISTANTS")
        
        timestamp = self.start_time.strftime('%Y%m%d-%H%M%S')
        backup_count = 0
        
        for script_info in SCRIPTS_CHAIN:
            output_file = script_info["output_file"]
            if os.path.exists(output_file):
                backup_name = f"{output_file}.backup-{timestamp}"
                try:
                    shutil.copy2(output_file, backup_name)
                    self.logger.info(f"  💾 {output_file} → {backup_name}")
                    backup_count += 1
                except Exception as e:
                    self.logger.warning(f"  ⚠️  Impossible de sauvegarder {output_file} : {e}")
        
        if backup_count > 0:
            self.logger.info(f"✅ {backup_count} fichiers sauvegardés")
        else:
            self.logger.info("✅ Aucun fichier existant à sauvegarder")

    def validate_file(self, filepath, min_rows=1):
        """Valider qu'un fichier est correctement créé"""
        # Cas spécial pour le script 12 de validation qui ne crée pas de fichier
        if filepath == "validation":
            return True, "Script de validation (pas de fichier de sortie)"
            
        if not os.path.exists(filepath):
            return False, "Fichier non créé"
        
        # Si c'est un répertoire (pour le script d'images)
        if os.path.isdir(filepath):
            try:
                files_count = len([f for f in os.listdir(filepath) if os.path.isfile(os.path.join(filepath, f))])
                if files_count == 0:
                    return False, "Répertoire vide"
                return True, f"OK ({files_count} fichiers créés)"
            except Exception as e:
                return False, f"Erreur lecture répertoire : {e}"
        
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return False, "Fichier vide"
        
        # Pour les fichiers Excel, vérifier le nombre de lignes
        if filepath.endswith('.xlsx'):
            try:
                # Utiliser subprocess pour valider dans l'environnement virtuel
                result = subprocess.run(
                    [self.python_venv, "-c", 
                     f"import openpyxl; wb=openpyxl.load_workbook('{filepath}'); print(wb.active.max_row); wb.close()"],
                    capture_output=True, text=True, check=True
                )
                actual_rows = int(result.stdout.strip())
                
                if actual_rows < min_rows:
                    return False, f"Trop peu de lignes ({actual_rows})"
                
                return True, f"OK ({actual_rows} lignes, {file_size:,} octets)"
            except Exception as e:
                return False, f"Erreur lecture Excel : {e}"
        
        # Pour les fichiers CSV
        elif filepath.endswith('.csv'):
            try:
                with open(filepath, 'r', encoding='utf-16') as f:
                    lines = sum(1 for line in f)
                
                if lines < min_rows:
                    return False, f"Trop peu de lignes ({lines})"
                
                return True, f"OK ({lines} lignes, {file_size:,} octets)"
            except Exception as e:
                return False, f"Erreur lecture CSV : {e}"
        
        return True, f"OK ({file_size:,} octets)"

    def update_image_path_in_script(self):
        """Mettre à jour le chemin des images dans le script 7"""
        script_path = os.path.join(SCRIPTS_DIR, "7-add_pathimg_excel.py")
        
        if self.image_path != DEFAULT_IMAGE_PATH:
            self.logger.info(f"🔧 Mise à jour du chemin d'images dans {script_path}")
            
            try:
                # Lire le contenu du script
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Remplacer le chemin par défaut
                old_line = f'IMAGE_BASE_PATH = "{DEFAULT_IMAGE_PATH}"'
                new_line = f'IMAGE_BASE_PATH = "{self.image_path}"'
                
                if old_line in content:
                    content = content.replace(old_line, new_line)
                    
                    # Écrire le fichier modifié
                    with open(script_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.logger.info(f"✅ Chemin d'images mis à jour dans {script_path}")
                else:
                    self.logger.warning(f"⚠️  Ligne à remplacer non trouvée dans {script_path}")
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur lors de la mise à jour de {script_path} : {e}")

    def execute_script(self, script_info, step_number):
        """Exécuter un script individuel"""
        script_name = script_info["script"]
        description = script_info["description"]
        output_file = script_info["output_file"]
        
        self.logger.info(f"🔄 ÉTAPE {step_number}/{len(SCRIPTS_CHAIN)} : {description}")
        self.logger.info(f"   Script : {script_name}")
        self.logger.info(f"   Sortie attendue : {output_file}")
        
        start_time = time.time()
        
        try:
            # Exécuter le script
            result = subprocess.run(
                [self.python_venv, script_name],
                check=True,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            execution_time = time.time() - start_time
            
            # Valider le fichier de sortie
            is_valid, validation_msg = self.validate_file(output_file)
            
            if is_valid:
                self.logger.info(f"✅ Script exécuté avec succès en {execution_time:.2f}s")
                self.logger.info(f"✅ Validation : {validation_msg}")
                
                # Enregistrer les statistiques
                self.stats['scripts_executed'] += 1
                self.stats['files_created'].append(output_file)
                self.stats['execution_times'][script_name] = execution_time
                
                # Ignorer le calcul de taille pour le script de validation
                if output_file != "validation":
                    if os.path.isdir(output_file):
                        # Pour les répertoires, calculer la taille totale
                        total_size = sum(os.path.getsize(os.path.join(output_file, f)) 
                                       for f in os.listdir(output_file) 
                                       if os.path.isfile(os.path.join(output_file, f)))
                        self.stats['file_sizes'][output_file] = total_size
                    else:
                        self.stats['file_sizes'][output_file] = os.path.getsize(output_file)
                
                if self.verbose and result.stdout:
                    self.logger.debug(f"Sortie du script :\n{result.stdout}")
                
                return True
                
            else:
                self.logger.error(f"❌ Validation échouée : {validation_msg}")
                self.stats['errors'].append(f"{script_name}: Validation échouée - {validation_msg}")
                return False
                
        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Erreur d'exécution après {execution_time:.2f}s")
            self.logger.error(f"Code de retour : {e.returncode}")
            
            if e.stdout:
                self.logger.error(f"Sortie standard :\n{e.stdout}")
            if e.stderr:
                self.logger.error(f"Erreur standard :\n{e.stderr}")
                
            self.stats['errors'].append(f"{script_name}: Erreur d'exécution (code {e.returncode})")
            return False
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Erreur inattendue après {execution_time:.2f}s : {e}")
            self.stats['errors'].append(f"{script_name}: Erreur inattendue - {str(e)}")
            return False

    def generate_final_report(self):
        """Générer le rapport final"""
        end_time = datetime.now()
        total_duration = end_time - self.start_time
        
        report_filename = f"sircom-rapport-{self.start_time.strftime('%Y%m%d-%H%M%S')}.txt"
        
        # Calculer les statistiques
        total_files_size = sum(self.stats['file_sizes'].values())
        average_execution_time = (
            sum(self.stats['execution_times'].values()) / len(self.stats['execution_times'])
            if self.stats['execution_times'] else 0
        )
        
        report_content = f"""
==================================================================================
📊 RAPPORT DE TRAITEMENT SIRCOM - MADE IN FRANCE 2025
==================================================================================

📅 INFORMATIONS GÉNÉRALES
-------------------------
Date de début       : {self.start_time.strftime('%d/%m/%Y à %H:%M:%S')}
Date de fin         : {end_time.strftime('%d/%m/%Y à %H:%M:%S')}
Durée totale        : {total_duration}
Fichier de log      : {self.log_filename}
Mode verbose        : {'Oui' if self.verbose else 'Non'}
Chemin des images   : {self.image_path}

📈 STATISTIQUES D'EXÉCUTION
----------------------------
Scripts exécutés    : {self.stats['scripts_executed']}/{len(SCRIPTS_CHAIN)}
Fichiers créés      : {len(self.stats['files_created'])}
Erreurs rencontrées : {len(self.stats['errors'])}
Temps moyen/script  : {average_execution_time:.2f} secondes
Espace disque total : {total_files_size:,} octets ({total_files_size/1024/1024:.2f} MB)

⏱️  TEMPS D'EXÉCUTION PAR SCRIPT
---------------------------------
"""
        
        for script_name, exec_time in self.stats['execution_times'].items():
            report_content += f"{script_name:<40} : {exec_time:>8.2f}s\n"
        
        report_content += f"""
📁 FICHIERS CRÉÉS
-----------------
"""
        
        for filename in self.stats['files_created']:
            if filename == "validation":
                # Script de validation - pas de fichier physique
                report_content += f"{filename:<50} : Script de validation (pas de fichier)\n"
            elif os.path.exists(filename):
                if os.path.isdir(filename):
                    # Pour les répertoires, afficher le nombre de fichiers
                    files_count = len([f for f in os.listdir(filename) 
                                     if os.path.isfile(os.path.join(filename, f))])
                    size = self.stats['file_sizes'].get(filename, 0)
                    report_content += f"{filename:<50} : {files_count} fichiers, {size:>10,} octets\n"
                else:
                    size = os.path.getsize(filename)
                    report_content += f"{filename:<50} : {size:>10,} octets\n"
        
        if self.stats['errors']:
            report_content += f"""
❌ ERREURS RENCONTRÉES
----------------------
"""
            for error in self.stats['errors']:
                report_content += f"• {error}\n"
        
        # Déterminer le résultat final
        if self.stats['scripts_executed'] == len(SCRIPTS_CHAIN) and not self.stats['errors']:
            status = "✅ SUCCÈS COMPLET"
            result_msg = "Tous les scripts ont été exécutés avec succès !"
        elif self.stats['scripts_executed'] > 0:
            status = "⚠️  SUCCÈS PARTIEL"
            result_msg = f"{self.stats['scripts_executed']}/{len(SCRIPTS_CHAIN)} scripts exécutés"
        else:
            status = "❌ ÉCHEC"
            result_msg = "Aucun script n'a pu être exécuté correctement"
        
        report_content += f"""
🎯 RÉSULTAT FINAL
-----------------
Statut : {status}
{result_msg}

📂 LIVRABLES FINAUX
-------------------
• Livrable Excel  : 5-livrable-final-word.xlsx
• Livrable CSV    : 9-final-sircom-indesign-utf16.csv
• Images traitées : export_images_id_dossier_rename_resize/

==================================================================================
Rapport généré automatiquement le {end_time.strftime('%d/%m/%Y à %H:%M:%S')}
==================================================================================
"""
        
        # Écrire le rapport
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"📊 Rapport final généré : {report_filename}")
            
            # Afficher le résumé dans les logs
            self.logger.info("="*80)
            self.logger.info("🎯 RÉSUMÉ FINAL")
            self.logger.info("="*80)
            self.logger.info(f"Statut : {status}")
            self.logger.info(f"Scripts exécutés : {self.stats['scripts_executed']}/{len(SCRIPTS_CHAIN)}")
            self.logger.info(f"Durée totale : {total_duration}")
            self.logger.info(f"Fichiers créés : {len(self.stats['files_created'])}")
            self.logger.info(f"Rapport détaillé : {report_filename}")
            
            return True, report_filename
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la génération du rapport : {e}")
            return False, None

    def run(self):
        """Exécuter la chaîne complète de traitement"""
        try:
            self.print_header()
            
            # Étape 1 : Vérifications préliminaires
            if not self.check_prerequisites():
                self.logger.error("❌ Prérequis non satisfaits - Arrêt du traitement")
                return False
            
            # Étape 2 : Configuration du chemin des images
            self.configure_image_path()
            
            # Étape 3 : Configuration de l'environnement
            if not self.setup_virtual_environment():
                self.logger.error("❌ Impossible de configurer l'environnement virtuel")
                return False
            
            # Étape 4 : Sauvegarde des fichiers existants
            self.backup_existing_files()
            
            # Étape 5 : Mise à jour du chemin d'images si nécessaire
            self.update_image_path_in_script()
            
            # Étape 6 : Exécution de la chaîne de scripts
            self.logger.info("🚀 DÉBUT DE L'EXÉCUTION DE LA CHAÎNE")
            self.logger.info("="*80)
            
            for i, script_info in enumerate(SCRIPTS_CHAIN, 1):
                if not self.execute_script(script_info, i):
                    self.logger.error(f"❌ Échec à l'étape {i} - Arrêt du traitement")
                    break
                    
                # Petite pause entre les scripts
                time.sleep(0.5)
            
            # Étape 7 : Génération du rapport final
            self.logger.info("="*80)
            self.logger.info("📊 GÉNÉRATION DU RAPPORT FINAL")
            
            success, report_file = self.generate_final_report()
            
            if success:
                self.logger.info("🎉 TRAITEMENT TERMINÉ AVEC SUCCÈS !")
                if report_file:
                    print(f"\n📊 Rapport détaillé disponible : {report_file}")
                return True
            else:
                self.logger.error("❌ Erreur lors de la génération du rapport")
                return False
                
        except KeyboardInterrupt:
            self.logger.warning("\n⚠️  Traitement interrompu par l'utilisateur")
            return False
        except Exception as e:
            self.logger.error(f"❌ Erreur critique : {e}")
            return False


# ==========================================
# POINT D'ENTRÉE PRINCIPAL
# ==========================================

def main():
    """Point d'entrée principal du script"""
    parser = argparse.ArgumentParser(
        description="Script maître pour la chaîne de traitement Sircom - Made in France 2025",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  python3 sircom_master_script.py              # Exécution normale
  python3 sircom_master_script.py --verbose    # Mode verbose avec logs détaillés
        """
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mode verbose - affichage détaillé des logs'
    )
    
    args = parser.parse_args()
    
    # Créer et lancer le processeur
    processor = SircomMasterProcessor(verbose=args.verbose)
    success = processor.run()
    
    # Code de sortie
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
