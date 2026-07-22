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
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from openpyxl import Workbook
import uvicorn

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.database import Database
from sircom2026.state import complete_step, fail_step
from sircom2026.worker_runner import run_worker_once


def make_settings(tmpdir: Path):
    return load_settings(
        {
            "SIRCOM_DATA_DIR": str(tmpdir / "data"),
            "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
            "SIRCOM_DISK_FREE_MIN_MB": "0",
            "SIRCOM_WORKER_ENABLED": "false",
        }
    )


class LiveServer:
    def __init__(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(("127.0.0.1", 0))
        self.port = int(self._server_socket.getsockname()[1])
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
        self.thread = threading.Thread(
            target=self.server.run,
            kwargs={"sockets": [self._server_socket]},
            daemon=True,
        )

    def __enter__(self) -> LiveServer:
        self.thread.start()
        self._wait_until_ready()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self._server_socket.close()
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
    def test_dom_contract_keeps_home_and_workflow_hooks(self) -> None:
        with LiveServer() as server:
            lot = server.create_lot("Lot Playwright Contrat DOM")
            lot_id = str(lot["id"])

            with chromium_browser() as browser:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(f"{server.base_url}/?lot_id={lot_id}", wait_until="networkidle")

                self.assertEqual(page.locator("main#contenu").count(), 1)
                self.assertEqual(page.locator("#ui-message [data-error-title]").count(), 1)
                self.assertEqual(page.locator("#ui-message [data-error-cause]").count(), 1)
                self.assertEqual(page.locator("#ui-message [data-error-action]").count(), 1)
                self.assertEqual(
                    page.locator("nav[aria-label='vous êtes ici :'] #breadcrumb-lot").count(),
                    1,
                )
                self.assertTrue(
                    page.evaluate(
                        """() => {
                            const ids = [
                                "create-lot-form",
                                "lots-panel",
                                "lot-summary",
                                "lot-actions",
                                "overview-title",
                            ];
                            const nodes = ids.map((id) => document.getElementById(id));
                            return nodes.every(Boolean)
                                && nodes.slice(0, -1).every((node, index) => (
                                    node.compareDocumentPosition(nodes[index + 1])
                                    & Node.DOCUMENT_POSITION_FOLLOWING
                                ));
                        }"""
                    )
                )

                delete_button = page.locator("#delete-lot-button")
                self.assertEqual(delete_button.get_attribute("data-lot-id"), lot_id)
                self.assertEqual(
                    delete_button.get_attribute("data-lot-title"),
                    "Lot Playwright Contrat DOM",
                )

                excel_form = page.locator("#excel-upload-form")
                self.assertEqual(excel_form.get_attribute("data-excel-upload-lot-id"), lot_id)
                self.assertIn(
                    "excel-file-hint",
                    page.locator("#excel-file").get_attribute("aria-describedby") or "",
                )
                self.assertEqual(
                    page.locator("#excel-file-selected-message").get_attribute(
                        "data-file-selected-message"
                    ),
                    "excel",
                )
                self.assertEqual(
                    page.locator("#excel-upload-submit").get_attribute("data-upload-submit"),
                    "excel",
                )

                image_form = page.locator("#image-upload-form")
                self.assertEqual(image_form.get_attribute("data-image-upload-lot-id"), lot_id)
                self.assertIn(
                    "image-zip-file-hint",
                    page.locator("#image-zip-file").get_attribute("aria-describedby") or "",
                )
                self.assertEqual(
                    page.locator("#image-zip-file-selected-message").get_attribute(
                        "data-file-selected-message"
                    ),
                    "images",
                )
                self.assertEqual(
                    page.locator("#image-upload-submit").get_attribute("data-upload-submit"),
                    "images",
                )

                page.goto(
                    f"{server.base_url}/lots/{lot_id}/excel?view=upload_excel",
                    wait_until="networkidle",
                )

                self.assertEqual(page.locator("#workflow-screens-title").count(), 1)
                self.assertEqual(
                    page.locator(".sircom-workflow-screens [aria-current='page']").count(),
                    1,
                )
                self.assertEqual(page.locator("#steps-menu-list").count(), 1)
                self.assertTrue(
                    page.locator(
                        "#lot-workspace[aria-labelledby='lot-workspace-title']"
                    ).is_visible()
                )
                self.assertEqual(
                    page.locator(".fr-sidemenu__link[aria-current='page']").count(),
                    1,
                )
                self.assertEqual(
                    page.locator("#timeline-title").get_attribute("aria-controls"),
                    "timeline-panel",
                )
                self.assertEqual(
                    page.locator("#lot-problems-title").get_attribute("aria-controls"),
                    "lot-problems-panel",
                )
                self.assertEqual(
                    page.locator("#lot-events-title").get_attribute("aria-controls"),
                    "lot-events-panel",
                )

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
                self.assertTrue(page.get_by_text("Étape 1 sur 13").first.is_visible())
                self.assertTrue(page.get_by_role("link", name="Ouvrir le parcours").is_visible())
                self.assertEqual(
                    page.get_by_role("button", name="Historique technique des étapes").count(),
                    0,
                )
                self.assertEqual(page.get_by_role("heading", name="Package final", exact=True).count(), 0)
                self.assertTrue(page.get_by_role("button", name="Déposer l'Excel source").is_visible())

                page.get_by_role("link", name="Ouvrir le parcours").click()
                page.wait_for_url(re.compile(r".*/lots/lot_.*/excel.*"), timeout=5000)
                self.assertTrue(
                    page.get_by_role("button", name="Historique technique des étapes").is_visible()
                )
                self.assertTrue(
                    page.locator(".fr-sidemenu").get_by_text("Déposer l'Excel").first.is_visible()
                )
                self.assertEqual(page.get_by_role("button", name="Déposer l'Excel source").count(), 0)

                page.goto(server.base_url, wait_until="networkidle")
                page.get_by_role("link", name="Lot Playwright Desktop").click()
                page.wait_for_url(re.compile(r".*\?lot_id=lot_.*"), timeout=5000)

                self.assertTrue(page.locator("#lot-detail-title").is_visible())
                workbook_path = server.tmp_path / "playwright-upload.xlsx"
                write_workbook(workbook_path)
                excel_upload_button = page.get_by_role("button", name="Déposer l'Excel source")
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

                self.assertIn("uploaded=excel", page.url)
                self.assertNotIn("view=upload_excel", page.url)
                self.assertTrue(page.get_by_text("Votre document a bien été déposé").first.is_visible())
                self.assertEqual(
                    page.evaluate("document.activeElement && document.activeElement.id"),
                    "excel-upload-submit",
                )
                worker_result = run_worker_once(
                    settings=replace(server.settings, worker_enabled=True)
                )
                self.assertIn(worker_result.outcome, {"succeeded", "idle"})
                page.goto(
                    f"{server.base_url}/lots/{lot_id}/excel?view=diagnostic_excel",
                    wait_until="networkidle",
                )
                self.assertTrue(
                    page.get_by_role("heading", name="Vérifier l'Excel", exact=True).is_visible()
                )
                self.assertTrue(page.get_by_text("Excel importable").first.is_visible())
                self.assertTrue(
                    page.get_by_role("button", name="Historique technique des étapes").is_visible()
                )
                assert_png_screenshot(self, page.screenshot(full_page=True))

                page.goto(f"{server.base_url}/lots/{lot_id}/excel?view=mapping", wait_until="networkidle")
                self.assertTrue(
                    page.get_by_role("heading", name="Choisir les colonnes", exact=True).is_visible()
                )
                editable_exports = page.locator("[data-mapping-exported]:not([disabled])")
                editable_count = editable_exports.count()
                self.assertGreater(editable_count, 0)

                page.get_by_role("button", name="Tout désélectionner").click()
                self.assertEqual(
                    page.locator("[data-mapping-exported]:not([disabled]):checked").count(),
                    0,
                )
                page.get_by_role("button", name="Tout sélectionner").click()
                self.assertEqual(
                    page.locator("[data-mapping-exported]:not([disabled]):checked").count(),
                    editable_count,
                )

                page.goto(f"{server.base_url}/?lot_id={lot_id}", wait_until="networkidle")
                dialog_messages: list[str] = []

                def accept_delete_dialog(dialog) -> None:
                    dialog_messages.append(dialog.message)
                    dialog.accept()

                page.once("dialog", accept_delete_dialog)
                page.get_by_role("button", name="Supprimer le lot").click()
                self.assertTrue(dialog_messages)
                self.assertIn("Lot Playwright Desktop", dialog_messages[0])
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
                self.assertTrue(page.get_by_text("Étape 1 sur 13").first.is_visible())
                self.assertTrue(page.get_by_role("button", name="Supprimer le lot").is_visible())
                self.assertTrue(page.get_by_role("button", name="Déposer l'Excel source").is_visible())
                self.assertEqual(
                    page.get_by_role("heading", name="Choisir les colonnes", exact=True).count(),
                    0,
                )
                self.assertEqual(page.get_by_role("heading", name="Package final", exact=True).count(), 0)
                assert_png_screenshot(self, page.screenshot(full_page=True))

                page.goto(f"{server.base_url}/lots/{lot['id']}", wait_until="networkidle")

                self.assertTrue(
                    page.get_by_role("button", name="Historique technique des étapes").is_visible()
                )
                self.assertTrue(page.get_by_role("button", name="Étapes du traitement").is_visible())
                self.assertEqual(page.get_by_role("button", name="Déposer l'Excel source").count(), 0)

                page.goto(f"{server.base_url}/?lot_id=lot_missing", wait_until="networkidle")

                self.assertTrue(page.get_by_role("heading", name="Lot introuvable").is_visible())
                self.assertTrue(page.get_by_text("Cause :").is_visible())
                self.assertTrue(page.get_by_text("Action attendue :").is_visible())

    def test_retry_button_requeues_blocked_worker_step_from_timeline(self) -> None:
        with LiveServer() as server:
            lot = server.create_lot("Lot Playwright Relance")
            database = Database(
                server.settings.sqlite_path,
                busy_timeout_ms=server.settings.sqlite_busy_timeout_ms,
            )
            with database.transaction() as repositories:
                complete_step(
                    repositories,
                    lot_id=str(lot["id"]),
                    step_key="upload_excel",
                    run_id="run_playwright_excel_uploaded",
                )
                fail_step(
                    repositories,
                    lot_id=str(lot["id"]),
                    step_key="diagnostic_excel",
                    run_id="run_playwright_diagnostic_failed",
                    code="SIRCOM_PLAYWRIGHT_DIAGNOSTIC_FAILED",
                    title="Diagnostic interrompu",
                    cause="Le diagnostic de test est interrompu.",
                    action="Relancer le diagnostic depuis l'historique des étapes.",
                )

            with chromium_browser() as browser:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(
                    f"{server.base_url}/lots/{lot['id']}/excel?view=diagnostic_excel",
                    wait_until="networkidle",
                )

                diagnostic_section = page.locator(
                    "section[aria-labelledby='excel-diagnostic-title']"
                )
                self.assertTrue(
                    page.get_by_role(
                        "heading",
                        name="Vérifier l'Excel",
                        exact=True,
                    ).is_visible()
                )
                self.assertTrue(
                    diagnostic_section.get_by_text("Diagnostic interrompu").is_visible()
                )
                self.assertTrue(
                    diagnostic_section.get_by_text("Action attendue").first.is_visible()
                )

                page.get_by_role("button", name="Historique technique des étapes").click()
                retry_button = page.locator("#retry-diagnostic_excel")
                retry_button.wait_for(state="visible", timeout=5000)
                self.assertTrue(retry_button.is_visible())
                with page.expect_response(
                    lambda response: response.url.endswith(f"/api/lots/{lot['id']}/retry")
                    and response.request.method == "POST"
                ) as retry_response:
                    retry_button.click()
                self.assertEqual(retry_response.value.status, 202)
                page.wait_for_url(
                    re.compile(r".*/lots/lot_.*/excel.*view=diagnostic_excel"),
                    timeout=5000,
                )
                page.locator("#retry-diagnostic_excel").wait_for(
                    state="detached",
                    timeout=5000,
                )
                page.wait_for_load_state("networkidle")

                self.assertTrue(
                    page.get_by_role(
                        "button",
                        name="Historique technique des étapes",
                    ).is_visible()
                )

            step, job = wait_for_step_and_job_state(
                database,
                lot_id=str(lot["id"]),
                step_key="diagnostic_excel",
                step_status="pret",
                job_status="queued",
            )

        self.assertIsNotNone(step)
        self.assertEqual(step["status"], "pret")
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "queued")


def assert_png_screenshot(test_case: unittest.TestCase, screenshot: bytes) -> None:
    test_case.assertTrue(screenshot.startswith(b"\x89PNG\r\n\x1a\n"))
    test_case.assertGreater(len(screenshot), 10_000)


def wait_for_step_and_job_state(
    database: Database,
    *,
    lot_id: str,
    step_key: str,
    step_status: str,
    job_status: str,
    timeout: float = 5,
) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.monotonic() + timeout
    last_step: dict[str, Any] | None = None
    last_job: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        with database.session() as repositories:
            last_step = repositories.steps.get_by_lot_key(lot_id, step_key)
            last_job = repositories.jobs.get_active_for_step(
                lot_id=lot_id,
                step_key=step_key,
            )
        if (
            last_step is not None
            and last_job is not None
            and last_step["status"] == step_status
            and last_job["status"] == job_status
        ):
            return last_step, last_job
        time.sleep(0.1)

    observed_step = None if last_step is None else last_step["status"]
    observed_job = None if last_job is None else last_job["status"]
    raise AssertionError(
        f"Timed out waiting for {step_key}: "
        f"step={step_status!r}, job={job_status!r}; "
        f"observed step={observed_step!r}, job={observed_job!r}."
    )


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
