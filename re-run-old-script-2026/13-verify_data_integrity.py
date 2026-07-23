#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de vérification de l'intégrité des données
Compare le fichier Excel source avec le CSV final
pour s'assurer qu'aucune ligne n'a été décalée
"""

import csv
import re
import sys
import unicodedata

import openpyxl

from sircom2026_rules import (
    config_value,
    empty_cell_marker,
    image_id_for_dossier,
    imageid_column_name,
)


def normalize_header(value):
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9]", "", text.lower())


def find_column(columns, candidates):
    normalized_columns = {normalize_header(column): column for column in columns}
    for candidate in candidates:
        normalized_candidate = normalize_header(candidate)
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]
    for normalized, original in normalized_columns.items():
        if any(normalize_header(candidate) in normalized for candidate in candidates):
            return original
    raise ValueError(f"Colonne introuvable parmi : {', '.join(candidates)}")


def optional_column(columns, candidates, default=None):
    try:
        return find_column(columns, candidates)
    except ValueError:
        return empty_cell_marker() if default is None else default


def normalize_id(value):
    return "" if value is None else str(value).strip()


def read_excel_rows(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook.active
    rows_iter = worksheet.iter_rows(values_only=True)
    headers = ["" if value is None else str(value) for value in next(rows_iter)]
    rows = []
    for row in rows_iter:
        rows.append(
            {
                header: "" if value is None else str(value)
                for header, value in zip(headers, row, strict=False)
            }
        )
    workbook.close()
    return headers, rows


def read_csv_rows(path):
    with open(
        path,
        "r",
        encoding=config_value("csv_encoding", "utf-16"),
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        return reader.fieldnames or [], rows


def verify_data_integrity():
    print("=== VÉRIFICATION DE LA COHÉRENCE DES DONNÉES ===")
    print()

    try:
        # 1. Lire le fichier Excel source
        marker = empty_cell_marker()

        excel_file = config_value("step_00_output")
        excel_columns, excel_rows = read_excel_rows(excel_file)
        print(f"Excel source lu : {len(excel_rows)} lignes (hors en-tête)")

        # 2. Lire le CSV final
        csv_file = config_value("step_10_output")
        csv_columns, csv_rows = read_csv_rows(csv_file)
        print(f"CSV final lu : {len(csv_rows)} lignes (hors en-tête)")
        print()

        # 3. Extraire les données pour comparaison
        col_id_excel = find_column(
            excel_columns,
            [
                "Dossier ID",
                "f_id",
                "id dossier",
                "id_dossier",
                "ID du dossier",
                "B_ID",
            ],
        )
        col_produit_excel = optional_column(
            excel_columns, ["produit", "dénomination", "nom produit"]
        )
        col_entreprise_excel = optional_column(
            excel_columns, ["entreprise", "nom entreprise"]
        )
        col_image_excel = optional_column(
            excel_columns, ["photo", "image", "photo produit"]
        )
        col_id_csv = find_column(csv_columns, ["f_id", "id dossier", "id_dossier"])
        col_image_csv = find_column(csv_columns, [imageid_column_name()])
        col_entreprise_csv = optional_column(csv_columns, ["entreprise"])
        col_produit_csv = optional_column(csv_columns, ["produit", "denomina"])

        # Créer un dictionnaire des données Excel
        excel_data = {}
        duplicate_excel_ids = []
        for idx, row in enumerate(excel_rows):
            id_str = normalize_id(row.get(col_id_excel))
            if id_str not in [marker, ""]:
                if id_str in excel_data:
                    duplicate_excel_ids.append(id_str)
                excel_data[id_str] = {
                    "entreprise": str(row.get(col_entreprise_excel, ""))
                    if col_entreprise_excel != marker
                    else marker,
                    "produit": str(row.get(col_produit_excel, ""))
                    if col_produit_excel != marker
                    else marker,
                    "image_source": str(row.get(col_image_excel, ""))
                    if col_image_excel != marker
                    else marker,
                    "position_excel": idx + 1,
                }

        print("TABLEAU DE VÉRIFICATION DES CORRESPONDANCES :")
        print("=" * 120)
        print(
            f"{'Pos CSV':<8} {'ID':<10} {'Image ID':<25} {'Entreprise':<30} {'Produit':<30} {'Status':<15}"
        )
        print("-" * 120)

        # Vérifier chaque ligne du CSV
        errors = []
        warnings = []
        if duplicate_excel_ids:
            for duplicate_id in sorted(set(duplicate_excel_ids)):
                errors.append(f"ID dupliqué dans Excel source : {duplicate_id}")
        seen_csv_ids = set()

        for idx, row in enumerate(csv_rows):
            csv_id = normalize_id(row.get(col_id_csv))
            csv_image = str(row.get(col_image_csv, ""))
            csv_entreprise = (
                str(row.get(col_entreprise_csv, ""))
                if col_entreprise_csv != marker
                else marker
            )
            csv_produit = (
                str(row.get(col_produit_csv, ""))
                if col_produit_csv != marker
                else marker
            )
            if csv_id in seen_csv_ids:
                errors.append(f"Ligne {idx + 2}: ID dupliqué dans CSV final : {csv_id}")
            seen_csv_ids.add(csv_id)

            # Tronquer pour l'affichage
            entreprise_display = (
                csv_entreprise[:27] + "..."
                if len(csv_entreprise) > 30
                else csv_entreprise
            )
            produit_display = (
                csv_produit[:27] + "..." if len(csv_produit) > 30 else csv_produit
            )

            if csv_id in excel_data:
                excel_info = excel_data[csv_id]

                # Vérifier la cohérence image_id (avec normalisation)
                # Les IDs peuvent être alphanumériques, normaliser en minuscules
                expected_image = image_id_for_dossier(csv_id)
                if csv_image != expected_image:
                    status = "IMG ERR"
                    errors.append(
                        f"Ligne {idx + 2}: Image attendue {expected_image}, trouvée {csv_image}"
                    )
                # Vérifier si trié (position changée)
                elif excel_info["position_excel"] != idx + 1:
                    status = "TRI OK"
                    warnings.append(
                        f"ID {csv_id} déplacé de ligne {excel_info['position_excel']} à {idx + 2}"
                    )
                else:
                    status = "OK"

                print(
                    f"{idx + 2:<8} {csv_id:<10} {csv_image:<25} {entreprise_display:<30} {produit_display:<30} {status}"
                )
            else:
                print(
                    f"{idx + 2:<8} {csv_id:<10} {csv_image:<25} {entreprise_display:<30} {produit_display:<30} ID ABSENT"
                )
                errors.append(
                    f"Ligne {idx + 2}: ID {csv_id} non trouvé dans Excel source"
                )

        print()
        print("=" * 120)
        print("RÉSUMÉ DE LA VÉRIFICATION :")
        print()

        # Statistiques
        print("Statistiques :")
        print(f"  - Lignes dans Excel source : {len(excel_data)}")
        print(f"  - Lignes dans CSV final : {len(csv_rows)}")
        print(f"  - Différence : {len(excel_data) - len(csv_rows)} lignes")
        print()

        # IDs manquants dans le CSV
        csv_ids = set(normalize_id(row.get(col_id_csv)) for row in csv_rows)
        missing_ids = set(excel_data.keys()) - csv_ids
        if missing_ids:
            print("IDs présents dans Excel mais absents du CSV final :")
            for mid in sorted(missing_ids):
                print(f"    - ID {mid}: {excel_data[mid]['entreprise'][:50]}")

        print()

        # Résultat final
        if errors:
            print(f"{len(errors)} ERREURS DÉTECTÉES :")
            for err in errors[:5]:  # Afficher max 5 erreurs
                print(f"    {err}")
            if len(errors) > 5:
                print(f"    ... et {len(errors) - 5} autres erreurs")
        else:
            print("AUCUNE ERREUR DÉTECTÉE")

        if warnings:
            print(
                f"\n{len(warnings)} lignes ont été réorganisées (tri par région/département)"
            )
            # Afficher quelques exemples
            for warn in warnings[:3]:
                print(f"    {warn}")
            if len(warnings) > 3:
                print(f"    ... et {len(warnings) - 3} autres déplacements")

        print()

        print("VÉRIFICATION DES ASSOCIATIONS IMAGE/DOSSIER :")
        print()
        image_ok_count = 0
        for row in csv_rows:
            csv_id = normalize_id(row.get(col_id_csv))
            csv_image = str(row.get(col_image_csv, ""))
            expected_image = image_id_for_dossier(csv_id)
            if csv_image == expected_image:
                image_ok_count += 1
        print(f"  Associations image conformes : {image_ok_count}/{len(csv_rows)}")

        print()
        print("=" * 120)

        if not errors:
            print("VALIDATION RÉUSSIE - Le CSV est cohérent avec l'Excel source !")
            print(
                "   Les données ont été triées par région mais les associations ID/données sont correctes."
            )
        else:
            print("ATTENTION - Des incohérences ont été détectées !")

    except Exception as e:
        print(f"Erreur lors de la vérification : {e}")
        return False

    return len(errors) == 0


if __name__ == "__main__":
    success = verify_data_integrity()
    sys.exit(0 if success else 1)
