#!/usr/bin/env python3

### Ce script permet :

# Version simplifiée - Aucune date à formater dans la nouvelle structure
# Ce script copie simplement le fichier pour maintenir la cohérence de la chaîne

import shutil
import os

# 1. Définir les fichiers source et destination
input_file = "3-fusion-tri-region-departement.xlsx"
output_file = "4-changer-date.xlsx"

# 2. Vérifier que le fichier source existe
if not os.path.exists(input_file):
    print(f"Erreur : Le fichier '{input_file}' n'existe pas dans le répertoire courant.")
    print("Assurez-vous d'avoir exécuté le script '3-fusion_tri_region_departement.py' au préalable.")
    exit(1)

print(f"Traitement du fichier : {input_file}")

# 3. Copier le fichier
try:
    shutil.copy(input_file, output_file)
    print(f"Fichier copié : {output_file}")
    print("Note : Aucune colonne de date trouvée dans la nouvelle structure")
    print("    Les colonnes H-L contiennent maintenant des informations produit/entreprise")
    print("    Ce script est conservé pour la compatibilité de la chaîne")
    print("Opération terminée avec succès !")
except Exception as e:
    print(f"Erreur lors de la copie du fichier : {e}")
    exit(1)