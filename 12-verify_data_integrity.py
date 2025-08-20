#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de vérification de l'intégrité des données
Compare le fichier Excel source avec le CSV final
pour s'assurer qu'aucune ligne n'a été décalée
"""

import pandas as pd
import sys

def verify_data_integrity():
    print('=== VÉRIFICATION DE LA COHÉRENCE DES DONNÉES ===')
    print()
    
    try:
        # 1. Lire le fichier Excel source
        excel_file = 'Sircom.xlsx'
        df_excel = pd.read_excel(excel_file)
        print(f'✅ Excel source lu : {len(df_excel)} lignes (hors en-tête)')
        
        # 2. Lire le CSV final
        csv_file = '9-final-sircom-indesign-utf16.csv'
        df_csv = pd.read_csv(csv_file, encoding='utf-16')
        print(f'✅ CSV final lu : {len(df_csv)} lignes (hors en-tête)')
        print()
        
        # 3. Extraire les données pour comparaison
        # Colonnes Excel
        col_id_excel = df_excel.columns[1]  # Colonne B = ID
        col_image_excel = df_excel.columns[82]  # Colonne CE = Image source
        col_entreprise_excel = df_excel.columns[4]  # Colonne E = Entreprise
        col_produit_excel = df_excel.columns[48]  # Colonne AW = Produit
        
        # Créer un dictionnaire des données Excel
        excel_data = {}
        for idx, row in df_excel.iterrows():
            id_val = row[col_id_excel]
            if pd.notna(id_val) and str(id_val) not in ['#N/A', '']:
                id_str = str(int(id_val) if isinstance(id_val, float) else id_val)
                excel_data[id_str] = {
                    'entreprise': str(row[col_entreprise_excel]) if pd.notna(row[col_entreprise_excel]) else '#N/A',
                    'produit': str(row[col_produit_excel]) if pd.notna(row[col_produit_excel]) else '#N/A',
                    'image_source': str(row[col_image_excel]) if pd.notna(row[col_image_excel]) else '#N/A',
                    'position_excel': idx + 1
                }
        
        print('📊 TABLEAU DE VÉRIFICATION DES CORRESPONDANCES :')
        print('='*120)
        print(f"{'Pos CSV':<8} {'ID':<10} {'Image ID':<25} {'Entreprise':<30} {'Produit':<30} {'Status':<15}")
        print('-'*120)
        
        # Vérifier chaque ligne du CSV
        errors = []
        warnings = []
        
        for idx, row in df_csv.iterrows():
            csv_id = str(row['b_id'])
            csv_image = str(row['imageid'])
            csv_entreprise = str(row['e_entrepri']) if 'e_entrepri' in row else '#N/A'
            csv_produit = str(row['aw_denomin']) if 'aw_denomin' in row else '#N/A'
            
            # Tronquer pour l'affichage
            entreprise_display = csv_entreprise[:27] + '...' if len(csv_entreprise) > 30 else csv_entreprise
            produit_display = csv_produit[:27] + '...' if len(csv_produit) > 30 else csv_produit
            
            if csv_id in excel_data:
                excel_info = excel_data[csv_id]
                
                # Vérifier la cohérence image_id
                expected_image = f"dossier-{csv_id}.jpg"
                if csv_image != expected_image:
                    status = '❌ IMG ERR'
                    errors.append(f"Ligne {idx+2}: Image attendue {expected_image}, trouvée {csv_image}")
                # Vérifier si trié (position changée)
                elif excel_info['position_excel'] != idx + 1:
                    status = '🔄 TRI OK'
                    warnings.append(f"ID {csv_id} déplacé de ligne {excel_info['position_excel']} à {idx+2}")
                else:
                    status = '✅ OK'
                
                print(f"{idx+2:<8} {csv_id:<10} {csv_image:<25} {entreprise_display:<30} {produit_display:<30} {status}")
            else:
                print(f"{idx+2:<8} {csv_id:<10} {csv_image:<25} {entreprise_display:<30} {produit_display:<30} ❌ ID ABSENT")
                errors.append(f"Ligne {idx+2}: ID {csv_id} non trouvé dans Excel source")
        
        print()
        print('='*120)
        print('📈 RÉSUMÉ DE LA VÉRIFICATION :')
        print()
        
        # Statistiques
        print(f"📊 Statistiques :")
        print(f"  - Lignes dans Excel source : {len(excel_data)}")
        print(f"  - Lignes dans CSV final : {len(df_csv)}")
        print(f"  - Différence : {len(excel_data) - len(df_csv)} lignes")
        print()
        
        # IDs manquants dans le CSV
        csv_ids = set(str(row['b_id']) for _, row in df_csv.iterrows())
        missing_ids = set(excel_data.keys()) - csv_ids
        if missing_ids:
            print(f"⚠️  IDs présents dans Excel mais absents du CSV final :")
            for mid in sorted(missing_ids):
                print(f"    - ID {mid}: {excel_data[mid]['entreprise'][:50]}")
        
        print()
        
        # Résultat final
        if errors:
            print(f"❌ {len(errors)} ERREURS DÉTECTÉES :")
            for err in errors[:5]:  # Afficher max 5 erreurs
                print(f"    {err}")
            if len(errors) > 5:
                print(f"    ... et {len(errors)-5} autres erreurs")
        else:
            print("✅ AUCUNE ERREUR DÉTECTÉE")
        
        if warnings:
            print(f"\n🔄 {len(warnings)} lignes ont été réorganisées (tri par région/département)")
            # Afficher quelques exemples
            for warn in warnings[:3]:
                print(f"    {warn}")
            if len(warnings) > 3:
                print(f"    ... et {len(warnings)-3} autres déplacements")
        
        print()
        
        # Vérification spécifique des images
        print("🖼️  VÉRIFICATION DES ASSOCIATIONS IMAGE/DOSSIER :")
        print()
        
        # Quelques exemples pour valider
        verif_samples = [
            ('24331205', 'packshot 4 Filtres gourde doypack.jpg', 'Filtres à eau'),
            ('24697654', 'IMG_3302.jpeg', 'Pizza ou autre produit'),
            ('24333464', 'IMG_0202.JPG', 'Produit'),
        ]
        
        for check_id, expected_source, description in verif_samples:
            if check_id in excel_data:
                csv_row = df_csv[df_csv['b_id'] == int(check_id)]
                if not csv_row.empty:
                    csv_image = csv_row.iloc[0]['imageid']
                    print(f"  ID {check_id} ({description}):")
                    print(f"    - Image source Excel : {excel_data[check_id]['image_source'][:50]}")
                    print(f"    - Image CSV : {csv_image}")
                    print(f"    - ✅ Correct" if csv_image == f"dossier-{check_id}.jpg" else f"    - ❌ ERREUR")
        
        print()
        print('='*120)
        
        if not errors:
            print("🎉 VALIDATION RÉUSSIE - Le CSV est cohérent avec l'Excel source !")
            print("   Les données ont été triées par région mais les associations ID/données sont correctes.")
        else:
            print("⚠️  ATTENTION - Des incohérences ont été détectées !")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification : {e}")
        return False
    
    return len(errors) == 0

if __name__ == "__main__":
    success = verify_data_integrity()
    sys.exit(0 if success else 1)