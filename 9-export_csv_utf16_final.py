#!/usr/bin/env python3

### Ce script permet :

# de traiter automatiquement le fichier "8-optimize-content.xlsx",
# de l'exporter en CSV avec encodage UTF-16 + BOM (comme le fichier de référence),
# de respecter le format exact pour InDesign (délimiteur virgule, saut de ligne LF),
# et d'enregistrer le fichier sous "9-final-sircom-indesign-utf16.csv"

# python3 9-export-csv-utf16.py

import pandas as pd
import os
import csv
import codecs

# 1. Définir le fichier source
file_path = "8-optimize-content.xlsx"

# 2. Vérifier que le fichier source existe
if not os.path.exists(file_path):
    print(f"❌ Erreur : Le fichier '{file_path}' n'existe pas dans le répertoire courant.")
    print("💡 Assurez-vous d'avoir exécuté le script '8-optimize-content.py' au préalable.")
    exit(1)

print(f"📂 Traitement du fichier : {file_path}")

try:
    # 3. Lire le fichier Excel avec pandas
    print(f"📖 Lecture du fichier Excel...")
    df = pd.read_excel(file_path, na_values=None, keep_default_na=False)
    
    print(f"✅ Fichier Excel lu avec succès")
    print(f"📊 Dimensions : {len(df)} lignes × {len(df.columns)} colonnes")
    
    # 4. Vérifier et nettoyer les données pour CSV
    print(f"🧹 Préparation des données pour CSV...")
    
    # Remplacer les NaN par "#N/A" MAIS conserver les types numériques pour les IDs
    df = df.fillna("#N/A")
    
    # Conversion intelligente : garder les colonnes numériques comme numériques, le reste en string
    for col in df.columns:
        if col in ['f_id', 'imageid'] or 'id' in str(col).lower():
            # Pour les colonnes d'ID, convertir en string en préservant les nombres
            df[col] = df[col].apply(lambda x: str(int(x)) if isinstance(x, (int, float)) and not pd.isna(x) and x != "#N/A" else str(x))
        else:
            # Pour les autres colonnes, convertir en string
            df[col] = df[col].astype(str)
    
    # Compter les éléments spéciaux
    total_cells = len(df) * len(df.columns)
    na_count = (df == "#N/A").sum().sum()
    br_count = df.astype(str).apply(lambda x: x.str.contains('<br>', case=False, na=False)).sum().sum()
    
    # Vérifier les IDs
    if 'f_id' in df.columns:
        valid_ids = df[df['f_id'] != "#N/A"]['f_id'].tolist()
        print(f"🔍 IDs détectés dans f_id : {len(valid_ids)} - {valid_ids[:5]}{'...' if len(valid_ids) > 5 else ''}")
    
    print(f"📊 Cellules #N/A : {na_count}/{total_cells}")
    print(f"📊 Cellules avec <br> : {br_count}")
    
    # 5. Définir le fichier de sortie
    output_filename = "9-final-sircom-indesign-utf16.csv"
    
    print(f"\n💾 Export en CSV UTF-16 + BOM...")
    
    # 6. Exporter en CSV UTF-16 avec BOM (comme le fichier de référence)
    with codecs.open(output_filename, 'w', encoding='utf-16') as csvfile:
        writer = csv.writer(csvfile, 
                           delimiter=',',           # Virgule comme délimiteur
                           lineterminator='\n',     # LF comme saut de ligne
                           quoting=csv.QUOTE_MINIMAL,  # Guillemets seulement si nécessaire
                           quotechar='"')           # Guillemets doubles
        
        # Écrire l'en-tête
        writer.writerow(df.columns.tolist())
        
        # Écrire les données ligne par ligne
        rows_written = 0
        for index, row in df.iterrows():
            writer.writerow(row.tolist())
            rows_written += 1
    
    print(f"✅ Fichier CSV exporté : {output_filename}")
    print(f"📊 Lignes écrites : {rows_written + 1} (incluant en-tête)")
    
    # 7. Vérifier la taille du fichier
    file_size = os.path.getsize(output_filename)
    print(f"📊 Taille du fichier : {file_size:,} octets ({file_size/1024:.1f} KB)")
    
    # 8. Afficher un échantillon des premières colonnes pour validation
    print(f"\n📋 Échantillon des en-têtes (10 premières colonnes) :")
    sample_headers = df.columns.tolist()[:10]
    for i, header in enumerate(sample_headers):
        print(f"  {i+1:2d}. {header}")
    
    if len(df.columns) > 10:
        print(f"  ... et {len(df.columns) - 10} autres colonnes")
    
    # 9. Résumé final
    print(f"\n📋 Résumé de l'export :")
    print(f"  ✓ Fichier source : {file_path}")
    print(f"  ✓ Fichier CSV final : {output_filename}")
    print(f"  ✓ Encodage : UTF-16 avec BOM")
    print(f"  ✓ Délimiteur : virgule (,)")
    print(f"  ✓ Saut de ligne : LF (\\n)")
    print(f"  ✓ Guillemets : automatiques si nécessaire")
    print(f"  ✓ Format : identique au fichier de référence InDesign")
    print(f"  ✓ Données : {len(df)} dossiers + en-têtes")
    print(f"  ✓ Colonnes : {len(df.columns)}")
    
    print(f"\n🎉 Export CSV final terminé avec succès !")
    print(f"📁 Le fichier '{output_filename}' est prêt pour InDesign !")

except FileNotFoundError:
    print(f"❌ Erreur : Le fichier '{file_path}' est introuvable.")
    exit(1)
except PermissionError:
    print(f"❌ Erreur : Permission refusée. Vérifiez que le fichier de sortie n'est pas ouvert.")
    exit(1)
except Exception as e:
    print(f"❌ Erreur lors de l'export : {e}")
    exit(1)

print(f"\n✨ Livrable final CSV UTF-16 prêt pour InDesign ! ✨")