#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'extraction de l'onglet Départements vers Sircom.xlsx
=============================================================

Ce script extrait l'onglet "Départements" du fichier Excel multi-onglets
et le sauvegarde comme fichier Sircom.xlsx pour traitement ultérieur
avec la chaîne de scripts-traitement-sircom.

Auteur : Claude Assistant
Date : 17 septembre 2025
"""

import pandas as pd
import sys
import os
from pathlib import Path

def extract_departements_to_sircom():
    """
    Extrait l'onglet Départements et crée le fichier Sircom.xlsx
    """

    # Chemins des fichiers
    source_file = "/Users/alex/Desktop/Made-In-France/excel/2025.09.17-Dossier JURY national.xlsx"
    output_file = "/Users/alex/Desktop/Made-In-France/excel/Sircom.xlsx"

    print("=" * 60)
    print("EXTRACTION DE L'ONGLET DÉPARTEMENTS VERS SIRCOM.XLSX")
    print("=" * 60)
    print()

    # Vérifier que le fichier source existe
    if not os.path.exists(source_file):
        print(f"❌ ERREUR : Le fichier source n'existe pas :")
        print(f"   {source_file}")
        sys.exit(1)

    print(f"📂 Fichier source : {Path(source_file).name}")

    try:
        # Lire l'onglet Départements
        print("\n📖 Lecture de l'onglet 'Départements'...")
        df = pd.read_excel(source_file, sheet_name='Départements')

        # Afficher les informations sur les données
        print(f"\n✅ Onglet lu avec succès :")
        print(f"   - Nombre de lignes : {len(df)}")
        print(f"   - Nombre de colonnes : {len(df.columns)}")

        # Afficher un aperçu des colonnes
        print(f"\n📊 Aperçu des colonnes :")
        for i, col in enumerate(df.columns[:5]):
            print(f"   - Colonne {i}: {col}")
        if len(df.columns) > 5:
            print(f"   ... ({len(df.columns) - 5} colonnes supplémentaires)")

        # Sauvegarder dans le nouveau fichier
        print(f"\n💾 Sauvegarde vers : {Path(output_file).name}")

        # Si le fichier existe déjà, le sauvegarder
        if os.path.exists(output_file):
            backup_name = output_file.replace('.xlsx', '_backup.xlsx')
            print(f"⚠️  Le fichier existe déjà, création d'une sauvegarde : {Path(backup_name).name}")
            if os.path.exists(backup_name):
                os.remove(backup_name)
            os.rename(output_file, backup_name)

        # Écrire le fichier avec le formatage original préservé
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Départements', index=False)

        print(f"\n✅ Extraction terminée avec succès !")
        print(f"   Le fichier Sircom.xlsx est prêt pour le traitement.")

        # Vérification finale
        df_verif = pd.read_excel(output_file)
        print(f"\n🔍 Vérification du fichier créé :")
        print(f"   - Lignes : {len(df_verif)}")
        print(f"   - Colonnes : {len(df_verif.columns)}")

        if len(df_verif) == len(df) and len(df_verif.columns) == len(df.columns):
            print(f"   ✅ Intégrité des données confirmée")
        else:
            print(f"   ⚠️  Attention : différence détectée dans les dimensions")

    except Exception as e:
        print(f"\n❌ ERREUR lors de l'extraction : {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("📦 Prochaine étape :")
    print("   Copier Sircom.xlsx dans scripts-traitement-sircom/")
    print("   puis lancer : python3 sircom_master_script.py --verbose")
    print("=" * 60)

if __name__ == "__main__":
    extract_departements_to_sircom()