#!/usr/bin/env python3

### Ce script permet :

# de traiter automatiquement le fichier "2-image-id-adder-excel-fusion.xlsx",
# de trier les données par "O_Groupe instructeur" puis par "P_Département",
# et d'enregistrer le fichier trié sous "3-fusion-tri-region-departement.xlsx"

import openpyxl as xl
import itertools
import os

# 1. Définir le fichier source
file_path = "2-image-id-adder-excel-fusion.xlsx"

# 2. Vérifier que le fichier source existe
if not os.path.exists(file_path):
    print(f"❌ Erreur : Le fichier '{file_path}' n'existe pas dans le répertoire courant.")
    print("💡 Assurez-vous d'avoir exécuté le script '3-image-id-adder-excel-fusion.py' au préalable.")
    exit(1)

print(f"📂 Traitement du fichier : {file_path}")

# 3. Ouvrir le fichier Excel
try:
    workbook = xl.load_workbook(file_path)
    print(f"✅ Fichier ouvert avec succès")
except Exception as e:
    print(f"❌ Erreur lors de l'ouverture du fichier : {e}")
    exit(1)

try:
    # 4. Sélectionner la feuille active
    worksheet = workbook.active
    sheet_name = worksheet.title
    print(f"🔄 Traitement de la feuille : {sheet_name}")

    # 5. Récupération de l'en-tête de la feuille de calcul
    header = [cell.value for cell in next(worksheet.rows)]
    print(f"✅ {len(header)} colonnes détectées")

    # 6. Identification des index des colonnes de tri
    try:
        col_groupe_instructeur = header.index('O_Groupe instructeur')
        print(f"✅ Colonne 'O_Groupe instructeur' trouvée à l'index : {col_groupe_instructeur}")
    except ValueError:
        print("❌ Erreur : La colonne 'O_Groupe instructeur' n'a pas été trouvée.")
        print("📋 Colonnes disponibles contenant 'Groupe' :")
        for i, col in enumerate(header):
            if col and 'Groupe' in str(col):
                print(f"  - Index {i}: {col}")
        exit(1)

    try:
        col_departement = header.index('AC_Département')
        print(f"✅ Colonne 'AC_Département' trouvée à l'index : {col_departement}")
    except ValueError:
        print("❌ Erreur : La colonne 'AC_Département' n'a pas été trouvée.")
        print("📋 Colonnes disponibles contenant 'Département' :")
        for i, col in enumerate(header):
            if col and 'Département' in str(col):
                print(f"  - Index {i}: {col}")
        exit(1)

    # 7. Tri par groupe instructeur puis département
    print("🔄 Tri des données en cours...")
    
    # Fonction de tri qui gère les valeurs None et "#N/A"
    def sort_key(row):
        groupe = row[col_groupe_instructeur] if row[col_groupe_instructeur] is not None and row[col_groupe_instructeur] != "#N/A" else ''
        dept = row[col_departement] if row[col_departement] is not None and row[col_departement] != "#N/A" else ''
        return (str(groupe), str(dept))
    
    sorted_data = [header]  # Réinsère la ligne d'en-tête
    data_rows = list(itertools.islice(worksheet.values, 1, None))
    sorted_rows = sorted(data_rows, key=sort_key)
    sorted_data.extend(sorted_rows)
    
    print(f"✅ {len(sorted_rows)} lignes de données triées")

    # 8. Création d'un nouveau classeur Excel pour stocker les résultats triés
    new_workbook = xl.Workbook()
    new_worksheet = new_workbook.active
    print("✅ Nouveau classeur créé")

    # 9. Copie des données triées dans la nouvelle feuille de calcul
    for i, row in enumerate(sorted_data):
        new_worksheet.append(row)
        if i == 0:
            print("✅ En-têtes copiés")
        elif i <= 3:
            # Afficher quelques exemples de tri
            groupe_val = row[col_groupe_instructeur] if row[col_groupe_instructeur] not in [None, "#N/A"] else "Non renseigné"
            dept_val = row[col_departement] if row[col_departement] not in [None, "#N/A"] else "Non renseigné"
            print(f"  📝 Ligne {i}: {groupe_val} | {dept_val}")

    # 10. Enregistrement du nouveau fichier Excel
    output_file_path = "3-fusion-tri-region-departement.xlsx"
    new_workbook.save(output_file_path)
    print(f"✅ Fichier sauvegardé sous : {output_file_path}")
    print("🎉 Tri terminé avec succès !")

except Exception as e:
    print(f"❌ Erreur lors du traitement : {e}")
    exit(1)
finally:
    # 11. Fermer les fichiers Excel
    if 'workbook' in locals():
        workbook.close()
    if 'new_workbook' in locals():
        new_workbook.close()
    print("📁 Fichiers fermés")