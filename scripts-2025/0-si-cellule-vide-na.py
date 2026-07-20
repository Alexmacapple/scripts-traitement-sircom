#!/usr/bin/env python3

### Ce script permet :

# de traiter automatiquement le fichier "Sircom.xlsx", de remplir les cellules vides avec "#N/A",
# de conserver le formatage initial et d'enregistrer le fichier avec le suffixe "_vide_na"

# Créer un environnement virtuel
# python3 -m venv venv

# Activer l'environnement virtuel
# source venv/bin/activate

# Installer les modules
# pip3 install openpyxl pandas

# Lancer le script
# python 0-si-cellule-vide-na.py


import openpyxl
import pandas as pd
import os

# 1. Définir le chemin du fichier (dans le répertoire courant)
file_path = "Sircom.xlsx"

# Vérifier que le fichier existe
if not os.path.exists(file_path):
    print(f"Erreur : Le fichier '{file_path}' n'existe pas dans le répertoire courant.")
    exit(1)

print(f"Traitement du fichier : {file_path}")

# 2. Charger le fichier Excel avec pandas pour traiter les données
excel_file = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")

# 3. Remplacer les valeurs NaN par "#N/A" dans les DataFrames
for sheet_name, df in excel_file.items():
    print(f"Traitement de la feuille : {sheet_name}")
    excel_file[sheet_name] = df.fillna("#N/A")

# 4. Charger le fichier original avec openpyxl pour conserver le formatage
input_workbook = openpyxl.load_workbook(file_path)

# 5. Créer le nom de fichier de sortie avec le suffixe '_vide_na'
filename, extension = os.path.splitext(file_path)
output_filename = f"{filename}_vide_na{extension}"

# 6. Copier les données modifiées dans les feuilles du fichier original
for sheet_name in input_workbook.sheetnames:
    input_sheet = input_workbook[sheet_name]
    df = excel_file[sheet_name]
    
    print(f"Mise à jour de la feuille : {sheet_name}")
    
    # Parcourir toutes les lignes du DataFrame (y compris les en-têtes)
    for index, row in df.iterrows():
        for col_num, cell_value in enumerate(row, start=1):
            # index + 2 car pandas index commence à 0 et Excel à 1, plus ligne d'en-tête
            input_sheet.cell(row=index + 2, column=col_num, value=cell_value)

# 7. Sauvegarder le nouveau fichier Excel avec les données modifiées et le formatage original
input_workbook.save(output_filename)

print(f"Fichier sauvegardé sous : {output_filename}")
print("Traitement terminé avec succès !")