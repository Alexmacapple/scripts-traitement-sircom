from __future__ import annotations

import unittest
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "sircom2026" / "templates"
INDEX_TEMPLATE = TEMPLATE_ROOT / "index.html"
STATIC_ROOT = Path(__file__).resolve().parents[1] / "sircom2026" / "static"


class UiTableContractTest(unittest.TestCase):
    def test_lot_tables_are_not_constrained_to_workflow_side_column(self) -> None:
        html = INDEX_TEMPLATE.read_text(encoding="utf-8")
        workspace_start = html.index(
            '<section class="fr-col-12 fr-col-lg-8" id="lot-workspace"'
        )
        workspace_end = html.index("</section>", workspace_start)

        for marker in (
            "sircom-table-no-scroll",
            "sircom-mapping-columns-table",
            "sircom-csv-preview-table",
        ):
            self.assertGreater(html.index(marker), workspace_end)

    def test_mapping_columns_table_scrolls_horizontally_only(self) -> None:
        css = (STATIC_ROOT / "sircom.css").read_text(encoding="utf-8")

        self.assertIn(".sircom-mapping-columns-table .fr-table__content", css)
        self.assertIn(".sircom-mapping-columns-table .fr-table__container", css)
        self.assertIn("overflow-x: auto;", css)
        self.assertIn("overflow-y: hidden;", css)
        self.assertIn("min-width: 64rem;", css)
        self.assertIn("max-width: 0;", css)
        self.assertIn("white-space: normal;", css)
        self.assertIn(".sircom-mapping-source-header", css)
        self.assertIn("word-break: break-word;", css)

    def test_csv_preview_table_is_contained_and_horizontally_scrollable(self) -> None:
        css = (STATIC_ROOT / "sircom.css").read_text(encoding="utf-8")

        self.assertIn(".sircom-csv-preview-table .fr-table__content", css)
        self.assertIn(".sircom-csv-preview-table .fr-table__container", css)
        self.assertIn("max-width: 100%;", css)
        self.assertIn("overflow-x: auto;", css)
        self.assertIn("overflow-y: hidden;", css)
        self.assertIn("--sircom-csv-preview-columns", css)
        self.assertIn("min-width: max(64rem", css)
        self.assertIn(".sircom-csv-preview-table th", css)
        self.assertIn("word-break: break-word;", css)


if __name__ == "__main__":
    unittest.main()
