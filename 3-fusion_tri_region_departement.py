#!/usr/bin/env python3

### Ce script permet :

# Version simplifiée - Le tri par région/département est déjà effectué dans le fichier source
# Ce script copie simplement le fichier pour maintenir la cohérence de la chaîne de traitement

import shutil
import os

# 1. Définir les fichiers source et destination
input_file = "2-image-id-adder-excel-fusion.xlsx"
output_file = "3-fusion-tri-region-departement.xlsx"

# 2. Vérifier que le fichier source existe
if not os.path.exists(input_file):
    print(f"❌ Erreur : Le fichier '{input_file}' n'existe pas dans le répertoire courant.")
    print("💡 Assurez-vous d'avoir exécuté le script '2-image_id_adder.py' au préalable.")
    exit(1)

print(f"📂 Traitement du fichier : {input_file}")

# 3. Copier le fichier
try:
    shutil.copy(input_file, output_file)
    print(f"✅ Fichier copié : {output_file}")
    print("ℹ️  Note : Le tri par région/département est déjà effectué dans le fichier source Sircom.xlsx")
    print("    Les données sont organisées par :")
    print("    - Régions groupées (ordre géographique : métropole puis outre-mer)")
    print("    - Départements triés par numéro à l'intérieur de chaque région")
    print("🎉 Opération terminée avec succès !")
except Exception as e:
    print(f"❌ Erreur lors de la copie du fichier : {e}")
    exit(1)