from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sircom2026.excel_diagnostic import clean_indesign_header, diagnose_workbook
from sircom2026.synthetic_excels import CASES, create_synthetic_excels


REAL_SIRCOM1 = Path("livrables-miweb-2025/Sircom1.xlsx")
REAL_SIRCOM2 = Path("livrables-miweb-2025/Sircom2.xlsx")


class ExcelDiagnosticTest(unittest.TestCase):
    def test_synthetic_cases_have_expected_import_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = create_synthetic_excels(Path(tmpdir))

            for case in CASES:
                with self.subTest(case=case.name):
                    diagnostic = diagnose_workbook(paths[case.name])
                    self.assertEqual(
                        diagnostic.importable,
                        case.expected_importable,
                        diagnostic.blockers,
                    )

    def test_valid_fixture_exercises_multi_tab_id_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = create_synthetic_excels(Path(tmpdir), ["valid_multi_tabs"])
            diagnostic = diagnose_workbook(paths["valid_multi_tabs"])

        self.assertTrue(diagnostic.importable, diagnostic.blockers)
        sheets = {sheet.name: sheet for sheet in diagnostic.sheets}
        self.assertEqual(sheets["Dossiers"].id_candidates[0].column, "A")
        self.assertEqual(sheets["Etablissements"].id_candidates[0].column, "C")
        self.assertEqual(sheets["Images"].id_candidates[0].column, "B")
        self.assertTrue(sheets["Avis"].ignored)
        self.assertTrue(
            any("sans id_dossier" in warning for warning in diagnostic.warnings),
            diagnostic.warnings,
        )

    def test_2025_header_cleaning_rule_keeps_excel_letter_prefix(self) -> None:
        self.assertEqual(clean_indesign_header("B_ID"), "b_id")
        self.assertEqual(clean_indesign_header("CE_Une (seule) photo du produit candidat"), "ce_uneseul")
        self.assertEqual(clean_indesign_header("AC_Département"), "ac_departe")

    def test_refusal_reasons_are_actionable_for_common_bad_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = create_synthetic_excels(
                Path(tmpdir),
                ["missing_id", "duplicate_id", "ambiguous_id", "merged_cells", "hidden_column", "formula"],
            )
            expected_fragments = {
                "missing_id": "Colonne id_dossier non detectee.",
                "duplicate_id": "Valeurs id_dossier dupliquees",
                "ambiguous_id": "Plusieurs colonnes id_dossier candidates.",
                "merged_cells": "cellule(s) fusionnee(s).",
                "hidden_column": "colonne(s) masquee(s).",
                "formula": "Formules detectees.",
            }

            for case_name, fragment in expected_fragments.items():
                with self.subTest(case=case_name):
                    diagnostic = diagnose_workbook(paths[case_name])
                    self.assertFalse(diagnostic.importable)
                    self.assertIn(fragment, " ".join(diagnostic.blockers))

    def test_local_2024_2025_inputs_when_available(self) -> None:
        if not REAL_SIRCOM1.exists() or not REAL_SIRCOM2.exists():
            self.skipTest("Local Sircom1.xlsx and Sircom2.xlsx fixtures are not present.")

        sircom1 = diagnose_workbook(REAL_SIRCOM1)
        sircom2 = diagnose_workbook(REAL_SIRCOM2)

        self.assertFalse(sircom1.importable)
        self.assertIn("colonne(s) masquee(s)", " ".join(sircom1.blockers))
        self.assertIn("Formules detectees.", " ".join(sircom1.blockers))
        self.assertTrue(sircom2.importable, sircom2.blockers)


if __name__ == "__main__":
    unittest.main()
