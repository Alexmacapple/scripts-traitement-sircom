#!/usr/bin/env python3

### Ce script permet :

# de traiter automatiquement le fichier "3-fusion-tri-region-departement.xlsx",
# de convertir toutes les colonnes de dates au format français "dd/mm/yyyy",
# de conserver les valeurs "#N/A" pour les cellules vides,
# et d'enregistrer le fichier sous "4-changer-date.xlsx"

# H_Dernière mise à jour le
# I_Dernière mise à jour du dossier le
# J_Déposé le
# K_Passé en instruction le
# L_Traité le

# python3 4-changer-date-format.py


import pandas as pd
import os
from datetime import datetime

# Fonction pour convertir les dates et gérer les valeurs "#N/A"
def convert_date(date):
    if pd.isnull(date) or date == "#N/A" or date == "":
        return "#N/A"
    try:
        # Essayer de convertir la date
        if isinstance(date, str):
            # Si c'est une chaîne, essayer de la parser
            parsed_date = pd.to_datetime(date, errors='coerce')
        else:
            # Si c'est déjà un datetime, l'utiliser directement
            parsed_date = pd.to_datetime(date, errors='coerce')
        
        if pd.isnull(parsed_date):
            return "#N/A"
        else:
            return parsed_date.strftime('%d/%m/%Y')
    except:
        return "#N/A"

# 1. Définir le fichier source
file_path = "3-fusion-tri-region-departement.xlsx"

# 2. Vérifier que le fichier source existe
if not os.path.exists(file_path):
    print(f"❌ Erreur : Le fichier '{file_path}' n'existe pas dans le répertoire courant.")
    print("💡 Assurez-vous d'avoir exécuté le script '4-fusion-tri-region-departement.py' au préalable.")
    exit(1)

print(f"📂 Traitement du fichier : {file_path}")

try:
    # 3. Lecture du fichier Excel
    df = pd.read_excel(file_path)
    print(f"✅ Fichier chargé avec {len(df)} lignes et {len(df.columns)} colonnes")

    # 4. Définir les colonnes de dates à traiter
    date_columns = [
        "H_Dernière mise à jour le",
        "I_Dernière mise à jour du dossier le", 
        "J_Déposé le",
        "K_Passé en instruction le",
        "L_Traité le"
    ]

    print(f"\n🔄 Traitement des colonnes de dates...")
    
    # 5. Vérifier et traiter chaque colonne de date
    columns_processed = 0
    for col_name in date_columns:
        if col_name in df.columns:
            print(f"  📝 Formatage de la colonne : {col_name}")
            
            # Compter les valeurs avant traitement
            non_null_before = df[col_name].notna().sum()
            
            # Appliquer la conversion
            df[col_name] = df[col_name].apply(convert_date)
            
            # Compter les valeurs après traitement (exclure "#N/A")
            non_null_after = (df[col_name] != "#N/A").sum()
            
            print(f"    ✅ {non_null_after}/{non_null_before} dates formatées avec succès")
            columns_processed += 1
        else:
            print(f"  ⚠️  Colonne non trouvée : {col_name}")

    if columns_processed == 0:
        print("❌ Aucune colonne de date n'a été trouvée à traiter.")
        exit(1)

    print(f"\n✅ {columns_processed}/{len(date_columns)} colonnes de dates traitées")

    # 6. Enregistrement dans un nouveau fichier Excel
    output_file_path = '4-changer-date.xlsx'
    df.to_excel(output_file_path, index=False)
    print(f"✅ Fichier sauvegardé sous : {output_file_path}")
    print("🎉 Formatage des dates terminé avec succès !")

    # 7. Afficher quelques exemples de dates formatées
    print(f"\n📋 Exemples de dates formatées (première ligne avec des dates) :")
    for col_name in date_columns:
        if col_name in df.columns:
            # Trouver la première valeur non-"#N/A"
            first_date = df[df[col_name] != "#N/A"][col_name].iloc[0] if len(df[df[col_name] != "#N/A"]) > 0 else "#N/A"
            print(f"  {col_name}: {first_date}")

except Exception as e:
    print(f"❌ Erreur lors du traitement : {e}")
    exit(1)