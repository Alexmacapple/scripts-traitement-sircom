from __future__ import annotations

import json
import os
import re
import socket
import tempfile
import threading
import time
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from openpyxl import Workbook
import uvicorn

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.worker_runner import run_worker_once


def make_settings(tmpdir: Path):
    return load_settings(
        {
            "SIRCOM_DATA_DIR": str(tmpdir / "data"),
            "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
            "SIRCOM_DISK_FREE_MIN_MB": "0",
        }
    )


class LiveServer:
    def __init__(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.settings = make_settings(self.tmp_path)
        self.server = uvicorn.Server(
            uvicorn.Config(
                create_app(self.settings),
                host="127.0.0.1",
                port=self.port,
                access_log=False,
                log_level="error",
            )
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> LiveServer:
        self.thread.start()
        self._wait_until_ready()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self._tmpdir.cleanup()

    def create_lot(self, title: str) -> dict[str, object]:
        request = Request(
            f"{self.base_url}/api/lots",
            data=json.dumps({"title": title}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Idempotency-Key": f"test-{title}",
            },
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            return json.load(response)["lot"]

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + 10
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if not self.thread.is_alive():
                raise RuntimeError("The Uvicorn test server stopped before readiness.")
            try:
                with urlopen(f"{self.base_url}/health/ready", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (OSError, URLError) as exc:
                last_error = exc
            time.sleep(0.1)
        raise RuntimeError("The Uvicorn test server did not become ready.") from last_error


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def playwright_sync():
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        raise unittest.SkipTest("Playwright is not installed.")
    return sync_playwright()


@contextmanager
def chromium_browser() -> Iterator[Any]:
    with playwright_sync() as playwright:
        browser = playwright.chromium.launch()
        try:
            yield browser
        finally:
            browser.close()


@unittest.skipUnless(
    os.environ.get("SIRCOM_RUN_PLAYWRIGHT") == "1",
    "Set SIRCOM_RUN_PLAYWRIGHT=1 to run browser UI checks.",
)
class LotsPlaywrightTest(unittest.TestCase):
    def test_desktop_create_select_timeline_and_delete_lot(self) -> None:
        with LiveServer() as server:
            with chromium_browser() as browser:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(server.base_url, wait_until="networkidle")

                self.assertEqual(page.title(), "Sircom 2026")
                self.assertTrue(
                    page.get_by_role("heading", name="Créer ou reprendre un lot").is_visible()
                )

                page.get_by_label("Nom du lot").fill("Lot Playwright Desktop")
                page.get_by_role("button", name="Créer le lot").click()
                page.wait_for_url(re.compile(r".*\?lot_id=lot_.*"), timeout=5000)
                lot_id_match = re.search(r"lot_id=(lot_[^&]+)", page.url)
                self.assertIsNotNone(lot_id_match)
                lot_id = lot_id_match.group(1)

                self.assertTrue(page.locator("#lot-detail-title").is_visible())
                self.assertTrue(
                    page.get_by_role("button", name="Historique technique des étapes").is_visible()
                )
                self.assertTrue(page.get_by_text("Étape 1 sur 13").first.is_visible())
                self.assertTrue(page.get_by_text("Déposer l'Excel").first.is_visible())
                self.assertEqual(page.get_by_role("heading", name="Package final", exact=True).count(), 0)
                self.assertTrue(page.get_by_role("button", name="Uploader l'Excel source").is_visible())

                page.goto(server.base_url, wait_until="networkidle")
                page.get_by_role("link", name="Lot Playwright Desktop").click()
                page.wait_for_url(re.compile(r".*\?lot_id=lot_.*"), timeout=5000)

                self.assertTrue(page.locator("#lot-detail-title").is_visible())
                workbook_path = server.tmp_path / "playwright-upload.xlsx"
                write_workbook(workbook_path)
                excel_upload_button = page.get_by_role("button", name="Uploader l'Excel source")
                self.assertTrue(excel_upload_button.is_enabled())
                self.assertEqual(excel_upload_button.get_attribute("data-upload-ready"), "false")
                page.get_by_label("Fichier Excel source").set_input_files(str(workbook_path))
                self.assertTrue(
                    page.get_by_text("Fichier sélectionné : playwright-upload.xlsx").is_visible()
                )
                self.assertTrue(excel_upload_button.is_enabled())
                self.assertEqual(excel_upload_button.get_attribute("data-upload-ready"), "true")
                excel_upload_button.click()
                page.wait_for_load_state("networkidle")

                self.assertIn("view=upload_excel", page.url)
                self.assertTrue(page.get_by_text("Votre document a bien été uploadé").first.is_visible())
                self.assertEqual(
                    page.evaluate("document.activeElement && document.activeElement.id"),
                    "excel-upload-submit",
                )
                worker_result = run_worker_once(settings=server.settings)
                self.assertIn(worker_result.outcome, {"succeeded", "idle"})
                page.goto(f"{server.base_url}/?lot_id={lot_id}&view=diagnostic_excel", wait_until="networkidle")
                self.assertTrue(
                    page.get_by_role("heading", name="Vérifier l'Excel", exact=True).is_visible()
                )
                self.assertTrue(page.get_by_text("Excel importable").first.is_visible())
                self.assertTrue(
                    page.get_by_role("button", name="Historique technique des étapes").is_visible()
                )
                assert_png_screenshot(self, page.screenshot(full_page=True))

                page.get_by_role("button", name="Supprimer").click()
                page.wait_for_url(f"{server.base_url}/", timeout=5000)

                self.assertEqual(
                    page.get_by_role("link", name="Lot Playwright Desktop").count(),
                    0,
                )

    def test_mobile_detail_keeps_timeline_and_actions_visible(self) -> None:
        with LiveServer() as server:
            lot = server.create_lot("Lot Playwright Mobile")
            with chromium_browser() as browser:
                page = browser.new_page(
                    is_mobile=True,
                    viewport={"width": 390, "height": 844},
                )
                page.goto(f"{server.base_url}/?lot_id={lot['id']}", wait_until="networkidle")

                self.assertTrue(page.locator("#lot-detail-title").is_visible())
                self.assertTrue(
                    page.get_by_role("button", name="Historique technique des étapes").is_visible()
                )
                self.assertTrue(page.get_by_text("Étape 1 sur 13").first.is_visible())
                self.assertTrue(page.get_by_role("button", name="Supprimer").is_visible())
                self.assertTrue(page.get_by_role("button", name="Uploader l'Excel source").is_visible())
                self.assertEqual(
                    page.get_by_role("heading", name="Choisir les colonnes", exact=True).count(),
                    0,
                )
                self.assertEqual(page.get_by_role("heading", name="Package final", exact=True).count(), 0)
                assert_png_screenshot(self, page.screenshot(full_page=True))

                page.goto(f"{server.base_url}/?lot_id=lot_missing", wait_until="networkidle")

                self.assertTrue(page.get_by_role("heading", name="Lot introuvable").is_visible())
                self.assertTrue(page.get_by_text("Cause :").is_visible())
                self.assertTrue(page.get_by_text("Action attendue :").is_visible())


def assert_png_screenshot(test_case: unittest.TestCase, screenshot: bytes) -> None:
    test_case.assertTrue(screenshot.startswith(b"\x89PNG\r\n\x1a\n"))
    test_case.assertGreater(len(screenshot), 10_000)


def write_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Produits"
    sheet.append(["id_dossier", "nom_produit"])
    sheet.append(["DOSSIER-1", "Produit Playwright"])
    workbook.save(path)
    workbook.close()


if __name__ == "__main__":
    unittest.main()
