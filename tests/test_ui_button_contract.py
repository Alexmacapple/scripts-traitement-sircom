from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from tests.template_contracts import read_template_with_includes


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "sircom2026" / "templates"
TEMPLATE_PATHS = tuple(sorted(TEMPLATE_ROOT.rglob("*.html")))
STATIC_ROOT = Path(__file__).resolve().parents[1] / "sircom2026" / "static"
PRIMARY_ACTION_LABELS = (
    "Créer le lot",
    "Étape suivante",
    "Déposer l'Excel source",
    "Déposer le zip images produit",
    "Télécharger les images traitées",
    "Valider cette image",
    "Valider le mapping",
    "Confirmer le tri",
    "Valider l'aperçu CSV",
    "Télécharger le rapport métier",
    "Télécharger le rapport technique",
    "Télécharger le package final",
    "Générer le package final",
)


@dataclass
class ButtonElement:
    path: Path
    line: int
    tag: str
    attrs: dict[str, str]
    text_parts: list[str] = field(default_factory=list)
    hidden_depth: int = 0

    @property
    def classes(self) -> str:
        return self.attrs.get("class", "")

    @property
    def text(self) -> str:
        return " ".join("".join(self.text_parts).split())

    def __repr__(self) -> str:
        relative_path = self.path.relative_to(TEMPLATE_ROOT.parent)
        return f"{relative_path}:{self.line} <{self.tag} class={self.classes!r}> text={self.text!r}"


class ButtonParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.stack: list[ButtonElement] = []
        self.buttons: list[ButtonElement] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        classes = attributes.get("class", "")
        is_button_like = tag == "button" or (tag == "a" and "fr-btn" in classes.split())
        if is_button_like:
            line, _column = self.getpos()
            self.stack.append(ButtonElement(self.path, line, tag, attributes))
            return
        if self.stack:
            button = self.stack[-1]
            if button.hidden_depth > 0 or is_hidden_from_accessible_name(attributes):
                button.hidden_depth += 1
            else:
                button.text_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self.stack and self.stack[-1].hidden_depth == 0:
            self.stack[-1].text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        button = self.stack[-1]
        if tag == button.tag:
            self.buttons.append(self.stack.pop())
            return
        if button.hidden_depth > 0:
            button.hidden_depth -= 1


def is_hidden_from_accessible_name(attributes: dict[str, str]) -> bool:
    classes = attributes.get("class", "").split()
    return (
        "fr-sr-only" in classes
        or attributes.get("aria-hidden") == "true"
        or "hidden" in attributes
    )


def parse_buttons(path: Path) -> list[ButtonElement]:
    parser = ButtonParser(path)
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.buttons


class UiButtonContractTest(unittest.TestCase):
    def test_current_step_navigation_is_not_rendered_as_button(self) -> None:
        html = read_template_with_includes(TEMPLATE_ROOT / "index.html")

        self.assertIn(
            'class="fr-link {{ primary_action.icon_class }} fr-link--icon-right"',
            html,
        )
        self.assertNotIn(
            'class="fr-btn {{ primary_action.icon_class }} fr-btn--icon-left"',
            html,
        )
        self.assertIn(
            'class="fr-link fr-icon-arrow-left-line fr-link--icon-left"',
            html,
        )
        self.assertIn(
            'class="fr-link fr-icon-arrow-right-line fr-link--icon-right"',
            html,
        )
        self.assertNotIn(
            'class="fr-btn fr-btn--secondary fr-icon-arrow-left-line fr-btn--icon-left"',
            html,
        )
        step_navigation_buttons = [
            button
            for path in TEMPLATE_PATHS
            for button in parse_buttons(path)
            if button.text.startswith(("Étape précédente", "Étape suivante"))
            and "fr-btn" in button.classes.split()
        ]
        self.assertEqual(step_navigation_buttons, [])
        self.assertIn(
            'class="fr-link fr-icon-arrow-down-line fr-link--icon-right"',
            html,
        )
        self.assertNotIn(
            'class="fr-btn fr-btn--secondary fr-icon-arrow-down-line fr-btn--icon-left"',
            html,
        )

    def test_dsfr_buttons_have_visible_labels(self) -> None:
        unlabeled = [
            button
            for path in TEMPLATE_PATHS
            for button in parse_buttons(path)
            if not button.text
        ]

        self.assertEqual(
            unlabeled,
            [],
            "Every DSFR action button must keep a visible text label.",
        )

    def test_icon_buttons_use_visible_label_variant(self) -> None:
        icon_only = [
            button
            for path in TEMPLATE_PATHS
            for button in parse_buttons(path)
            if "fr-icon-" in button.classes
            and "fr-btn--icon-left" not in button.classes
            and "fr-btn--icon-right" not in button.classes
        ]

        self.assertEqual(
            icon_only,
            [],
            "Icon buttons must use the DSFR visible-label variant.",
        )

    def test_local_action_groups_do_not_collapse_icon_buttons_to_icon_only(self) -> None:
        css = (STATIC_ROOT / "sircom.css").read_text(encoding="utf-8")

        self.assertIn('.sircom-action-group .fr-btn[class*=" fr-icon-"]', css)
        self.assertIn("max-height: none;", css)
        self.assertIn("overflow: visible;", css)
        self.assertIn("width: auto;", css)

    def test_local_arrow_link_icons_have_masks(self) -> None:
        css = (STATIC_ROOT / "sircom.css").read_text(encoding="utf-8")

        for icon_name in ("arrow-left-line", "arrow-right-line", "arrow-down-line"):
            self.assertIn(f".fr-icon-{icon_name}::before", css)
            self.assertIn(f".fr-icon-{icon_name}::after", css)
            self.assertIn(f"/static/dsfr/1.14.4/icons/arrows/{icon_name}.svg", css)

    def test_primary_actions_are_not_secondary_buttons(self) -> None:
        buttons = [button for path in TEMPLATE_PATHS for button in parse_buttons(path)]
        secondary_primary_actions = [
            button
            for button in buttons
            if "fr-btn--secondary" in button.classes
            and any(label in button.text for label in PRIMARY_ACTION_LABELS)
        ]

        self.assertEqual(
            secondary_primary_actions,
            [],
            "Primary workflow actions must remain primary DSFR buttons.",
        )


if __name__ == "__main__":
    unittest.main()
