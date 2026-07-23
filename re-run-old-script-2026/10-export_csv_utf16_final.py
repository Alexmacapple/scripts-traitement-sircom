#!/usr/bin/env python3

### Ce script permet :

# de traiter automatiquement le fichier "09-optimize-content.xlsx",
# de l'exporter en CSV avec encodage UTF-16 + BOM (comme le fichier de référence),
# de respecter le format exact pour InDesign (délimiteur virgule, saut de ligne LF),
# et d'enregistrer le fichier sous "10-final-sircom-indesign-utf16.csv"

# python3 10-export_csv_utf16_final.py

import csv
import os

import openpyxl

from sircom2026_rules import config_value, empty_cell_marker, is_dossier_id_header


def cell_to_csv(value):
    marker = empty_cell_marker()
    if value is None:
        return marker
    text = str(value).strip()
    return text if text else marker


# 1. Définir le fichier source
file_path = config_value("step_09_output")

# 2. Vérifier que le fichier source existe
if not os.path.exists(file_path):
    print(f"Erreur : Le fichier '{file_path}' n'existe pas dans le répertoire courant.")
    print(
        "Assurez-vous d'avoir exécuté le script '09-optimize_content_excel.py' au préalable."
    )
    exit(1)

print(f"Traitement du fichier : {file_path}")

try:
    # 3. Lire le fichier Excel avec openpyxl pour éviter une dépendance pandas.
    print("Lecture du fichier Excel...")
    workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    worksheet = workbook.active
    rows_iter = worksheet.iter_rows(values_only=True)
    headers = [cell_to_csv(value) for value in next(rows_iter)]
    rows = [[cell_to_csv(value) for value in row] for row in rows_iter]
    workbook.close()

    print("Fichier Excel lu avec succès")
    print(f"Dimensions : {len(rows)} lignes × {len(headers)} colonnes")

    # 4. Vérifier et nettoyer les données pour CSV
    print("Préparation des données pour CSV...")

    # Compter les éléments spéciaux
    total_cells = len(rows) * len(headers)
    marker = empty_cell_marker()
    na_count = sum(value == marker for row in rows for value in row)
    br_count = sum("<br>" in value.lower() for row in rows for value in row)

    # Vérifier les IDs
    id_columns = [column for column in headers if is_dossier_id_header(column)]
    if id_columns:
        id_column = id_columns[0]
        id_index = headers.index(id_column)
        valid_ids = [row[id_index] for row in rows if row[id_index] != marker]
        print(
            f"IDs détectés dans {id_column} : {len(valid_ids)} - {valid_ids[:5]}{'...' if len(valid_ids) > 5 else ''}"
        )

    print(f"Cellules {marker} : {na_count}/{total_cells}")
    print(f"Cellules avec <br> : {br_count}")

    # 5. Définir le fichier de sortie
    output_filename = config_value("step_10_output")

    csv_encoding = config_value("csv_encoding", "utf-16")
    csv_delimiter = config_value("csv_delimiter", ",")
    line_terminator_config = config_value("csv_lineterminator", "LF")
    csv_lineterminator = (
        "\n" if line_terminator_config.upper() == "LF" else line_terminator_config
    )

    # 6. Exporter en CSV UTF-16 avec BOM (comme le fichier de référence)
    print(f"\nExport en CSV {csv_encoding}...")
    with open(output_filename, "w", encoding=csv_encoding, newline="") as csvfile:
        writer = csv.writer(
            csvfile,
            delimiter=csv_delimiter,
            lineterminator=csv_lineterminator,
            quoting=csv.QUOTE_MINIMAL,  # Guillemets seulement si nécessaire
            quotechar='"',
        )  # Guillemets doubles

        # Écrire l'en-tête
        writer.writerow(headers)

        # Écrire les données ligne par ligne
        rows_written = 0
        for row in rows:
            writer.writerow(row)
            rows_written += 1

    print(f"Fichier CSV exporté : {output_filename}")
    print(f"Lignes écrites : {rows_written + 1} (incluant en-tête)")

    # 7. Vérifier la taille du fichier
    file_size = os.path.getsize(output_filename)
    print(f"Taille du fichier : {file_size:,} octets ({file_size / 1024:.1f} KB)")

    # 8. Afficher un échantillon des premières colonnes pour validation
    print("\nÉchantillon des en-têtes (10 premières colonnes) :")
    sample_headers = headers[:10]
    for i, header in enumerate(sample_headers):
        print(f"  {i + 1:2d}. {header}")

    if len(headers) > 10:
        print(f"  ... et {len(headers) - 10} autres colonnes")

    # 9. Résumé final
    print("\nRésumé de l'export :")
    print(f"  Fichier source : {file_path}")
    print(f"  Fichier CSV final : {output_filename}")
    print(f"  Encodage : {csv_encoding}")
    print(f"  Délimiteur : {csv_delimiter}")
    print(f"  Saut de ligne : {line_terminator_config}")
    print("  Guillemets : automatiques si nécessaire")
    print("  Format : identique au fichier de référence InDesign")
    print(f"  Données : {len(rows)} dossiers + en-têtes")
    print(f"  Colonnes : {len(headers)}")

    print("\nExport CSV final terminé avec succès !")
    print(f"Le fichier '{output_filename}' est prêt pour InDesign !")

except FileNotFoundError:
    print(f"Erreur : Le fichier '{file_path}' est introuvable.")
    exit(1)
except PermissionError:
    print(
        "Erreur : Permission refusée. Vérifiez que le fichier de sortie n'est pas ouvert."
    )
    exit(1)
except Exception as e:
    print(f"Erreur lors de l'export : {e}")
    exit(1)

print("\nLivrable final CSV UTF-16 prêt pour InDesign !")
