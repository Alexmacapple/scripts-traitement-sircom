from __future__ import annotations

import os
import unittest
from typing import Any

from tests.test_lots_playwright import LiveServer, chromium_browser


def axe_checker():
    try:
        from axe_playwright_python.sync_playwright import Axe
    except ModuleNotFoundError:
        raise unittest.SkipTest("axe-playwright-python is not installed.")
    return Axe()


@unittest.skipUnless(
    os.environ.get("SIRCOM_RUN_PLAYWRIGHT") == "1",
    "Set SIRCOM_RUN_PLAYWRIGHT=1 to run Axe browser accessibility checks.",
)
class AxeAccessibilityTest(unittest.TestCase):
    def test_create_lot_form_is_named_by_visible_heading(self) -> None:
        with LiveServer() as server:
            with chromium_browser() as browser:
                page = browser.new_page(viewport={"width": 1366, "height": 900})
                try:
                    page.goto(server.base_url, wait_until="networkidle")

                    create_lot_form = page.locator("#create-lot-form")
                    self.assertEqual(
                        create_lot_form.get_attribute("aria-labelledby"),
                        "create-lot-title",
                    )
                    self.assertEqual(
                        page.locator("#create-lot-title").inner_text(),
                        "Créer ou reprendre un lot",
                    )
                finally:
                    page.close()

    def test_public_pages_and_lot_page_have_no_axe_violations(self) -> None:
        with LiveServer() as server:
            lot = server.create_lot("Lot Axe accessibilite")
            paths = [
                "/",
                "/accessibilite",
                "/donnees-personnelles",
                "/plan-du-site",
                f"/?lot_id={lot['id']}",
                f"/lots/{lot['id']}/excel?view=upload_excel",
                f"/lots/{lot['id']}/images?view=upload_images",
                f"/lots/{lot['id']}/export?view=rapports",
            ]

            with chromium_browser() as browser:
                axe = axe_checker()
                violations_by_path: dict[str, list[dict[str, Any]]] = {}
                for path in paths:
                    page = browser.new_page(viewport={"width": 1366, "height": 900})
                    try:
                        page.goto(f"{server.base_url}{path}", wait_until="networkidle")
                        results = axe.run(page)
                    finally:
                        page.close()

                    response = getattr(results, "response", {})
                    violations = (
                        response.get("violations", [])
                        if isinstance(response, dict)
                        else []
                    )
                    if violations:
                        violations_by_path[path] = [
                            {
                                "id": violation.get("id"),
                                "impact": violation.get("impact"),
                                "description": violation.get("description"),
                                "targets": [
                                    node.get("target")
                                    for node in violation.get("nodes", [])[:5]
                                ],
                            }
                            for violation in violations
                        ]

                self.assertEqual(violations_by_path, {})
