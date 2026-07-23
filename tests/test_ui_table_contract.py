from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path

from tests.template_contracts import read_template_with_includes


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "sircom2026" / "templates"
INDEX_TEMPLATE = TEMPLATE_ROOT / "index.html"
STATIC_ROOT = Path(__file__).resolve().parents[1] / "sircom2026" / "static"
LOT_TABLE_CLASSES = (
    "sircom-table-no-scroll",
    "sircom-mapping-columns-table",
    "sircom-csv-preview-table",
)


class DescendantClassParser(HTMLParser):
    def __init__(self, ancestor_id: str, class_names: tuple[str, ...]) -> None:
        super().__init__()
        self.ancestor_id = ancestor_id
        self.class_names = set(class_names)
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.matches: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        classes = set(attributes.get("class", "").split())
        matched_classes = sorted(classes & self.class_names)
        if matched_classes and self._is_inside_ancestor():
            line, _column = self.getpos()
            self.matches.append(f"line {line}: <{tag}> {', '.join(matched_classes)}")
        self.stack.append((tag, attributes))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def _is_inside_ancestor(self) -> bool:
        return any(
            attributes.get("id") == self.ancestor_id for _tag, attributes in self.stack
        )


class UiTableContractTest(unittest.TestCase):
    def test_lot_tables_are_not_constrained_to_workflow_side_column(self) -> None:
        html = read_template_with_includes(INDEX_TEMPLATE)
        parser = DescendantClassParser("lot-workspace", LOT_TABLE_CLASSES)
        parser.feed(html)

        for marker in LOT_TABLE_CLASSES:
            self.assertIn(marker, html)
        self.assertEqual(parser.matches, [])

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
