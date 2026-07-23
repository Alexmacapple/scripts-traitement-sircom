from __future__ import annotations

import os
import re
import stat
import tempfile
import unittest
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from sircom2026.app import create_app
from sircom2026.config import ConfigError, load_settings


@dataclass
class DiskUsage:
    total: int
    used: int
    free: int


@dataclass
class HtmlElement:
    tag: str
    attrs: dict[str, str]


class ShellHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[HtmlElement] = []
        self.elements_by_id: dict[str, HtmlElement] = {}
        self.asset_paths: list[str] = []
        self.anchor_refs: list[str] = []
        self.buttons: list[tuple[dict[str, str], str]] = []
        self._button_stack: list[tuple[dict[str, str], list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        element = HtmlElement(tag=tag, attrs=attr_map)
        self.elements.append(element)
        if tag == "button":
            self._button_stack.append((attr_map, []))

        element_id = attr_map.get("id")
        if element_id:
            self.elements_by_id[element_id] = element

        if tag == "a":
            href = attr_map.get("href", "")
            if href.startswith("#"):
                self.anchor_refs.append(href[1:])

        for key in ("href", "src"):
            path = attr_map.get(key, "")
            if path.startswith("/static/"):
                self.asset_paths.append(path)

    def handle_data(self, data: str) -> None:
        if self._button_stack:
            self._button_stack[-1][1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._button_stack:
            attrs, text_parts = self._button_stack.pop()
            self.buttons.append((attrs, " ".join(text_parts).strip()))


def make_settings(tmpdir: Path, **overrides: str):
    env = {
        "SIRCOM_DATA_DIR": str(tmpdir / "data"),
        "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
        "SIRCOM_DISK_FREE_MIN_MB": "0",
    }
    env.update(overrides)
    return load_settings(env)


class SettingsTest(unittest.TestCase):
    def test_default_settings(self) -> None:
        settings = load_settings({})

        self.assertEqual(settings.data_dir, Path(".sircom2026-data"))
        self.assertEqual(settings.sqlite_path, Path(".sircom2026-data/sircom.sqlite3"))
        self.assertEqual(settings.max_excel_mb, 50)
        self.assertEqual(settings.max_excel_rows, 200_000)
        self.assertEqual(settings.max_excel_columns, 256)
        self.assertEqual(settings.max_excel_cells, 5_000_000)
        self.assertEqual(settings.max_zip_mb, 1024)
        self.assertEqual(settings.max_image_count, 1500)
        self.assertEqual(settings.max_image_mb, 50)
        self.assertEqual(settings.max_image_pixels, 80_000_000)
        self.assertEqual(settings.max_image_width_px, 20_000)
        self.assertEqual(settings.max_image_height_px, 20_000)
        self.assertEqual(settings.max_unzipped_mb, 3072)
        self.assertEqual(
            settings.indesign_image_root, "/Users/victoria/Documents/export-jpg-resize"
        )
        self.assertEqual(settings.bind_host, "127.0.0.1")
        self.assertEqual(settings.port, 8000)
        self.assertTrue(settings.worker_enabled)
        self.assertEqual(settings.worker_id, "local-1")
        self.assertEqual(settings.max_active_jobs, 1)
        self.assertEqual(settings.worker_poll_seconds, 2)
        self.assertEqual(settings.worker_lease_ttl_seconds, 300)
        self.assertEqual(settings.worker_heartbeat_seconds, 30)
        self.assertEqual(settings.disk_free_min_mb, 5120)
        self.assertEqual(settings.purge_interval_seconds, 3600)
        self.assertEqual(settings.purge_trace_retention_days, 30)
        self.assertEqual(settings.sqlite_busy_timeout_ms, 5000)
        self.assertEqual(settings.artifact_pending_ttl_seconds, 3600)

    def test_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "SIRCOM_DATA_DIR": str(Path(tmp) / "custom-data"),
                "SIRCOM_SQLITE_PATH": str(Path(tmp) / "custom.sqlite3"),
                "SIRCOM_RETENTION_DAYS": "14",
                "SIRCOM_MAX_EXCEL_MB": "12",
                "SIRCOM_MAX_EXCEL_ROWS": "1234",
                "SIRCOM_MAX_EXCEL_COLUMNS": "56",
                "SIRCOM_MAX_EXCEL_CELLS": "7890",
                "SIRCOM_MAX_ZIP_MB": "99",
                "SIRCOM_MAX_IMAGE_COUNT": "42",
                "SIRCOM_MAX_IMAGE_MB": "8",
                "SIRCOM_MAX_IMAGE_PIXELS": "654321",
                "SIRCOM_MAX_IMAGE_WIDTH_PX": "4321",
                "SIRCOM_MAX_IMAGE_HEIGHT_PX": "3210",
                "SIRCOM_MAX_UNZIPPED_MB": "256",
                "SIRCOM_INDESIGN_IMAGE_ROOT": "/tmp/export-jpg-resize",
                "SIRCOM_BIND_HOST": "0.0.0.0",
                "SIRCOM_PORT": "9000",
                "SIRCOM_WORKER_ENABLED": "false",
                "SIRCOM_WORKER_ID": "worker-test",
                "SIRCOM_MAX_ACTIVE_JOBS": "2",
                "SIRCOM_WORKER_POLL_SECONDS": "5",
                "SIRCOM_WORKER_LEASE_TTL_SECONDS": "120",
                "SIRCOM_WORKER_HEARTBEAT_SECONDS": "10",
                "SIRCOM_DISK_FREE_MIN_MB": "128",
                "SIRCOM_PURGE_INTERVAL_SECONDS": "600",
                "SIRCOM_PURGE_TRACE_RETENTION_DAYS": "15",
                "SIRCOM_SQLITE_BUSY_TIMEOUT_MS": "2500",
                "SIRCOM_ARTIFACT_PENDING_TTL_SECONDS": "60",
            }

            settings = load_settings(env)

        self.assertEqual(settings.data_dir.name, "custom-data")
        self.assertEqual(settings.sqlite_path.name, "custom.sqlite3")
        self.assertEqual(settings.retention_days, 14)
        self.assertEqual(settings.max_excel_mb, 12)
        self.assertEqual(settings.max_excel_rows, 1234)
        self.assertEqual(settings.max_excel_columns, 56)
        self.assertEqual(settings.max_excel_cells, 7890)
        self.assertEqual(settings.max_zip_mb, 99)
        self.assertEqual(settings.max_image_count, 42)
        self.assertEqual(settings.max_image_mb, 8)
        self.assertEqual(settings.max_image_pixels, 654321)
        self.assertEqual(settings.max_image_width_px, 4321)
        self.assertEqual(settings.max_image_height_px, 3210)
        self.assertEqual(settings.max_unzipped_mb, 256)
        self.assertEqual(settings.indesign_image_root, "/tmp/export-jpg-resize")
        self.assertEqual(settings.bind_host, "0.0.0.0")
        self.assertEqual(settings.port, 9000)
        self.assertFalse(settings.worker_enabled)
        self.assertEqual(settings.worker_id, "worker-test")
        self.assertEqual(settings.max_active_jobs, 2)
        self.assertEqual(settings.worker_poll_seconds, 5)
        self.assertEqual(settings.worker_lease_ttl_seconds, 120)
        self.assertEqual(settings.worker_heartbeat_seconds, 10)
        self.assertEqual(settings.disk_free_min_mb, 128)
        self.assertEqual(settings.purge_interval_seconds, 600)
        self.assertEqual(settings.purge_trace_retention_days, 15)
        self.assertEqual(settings.sqlite_busy_timeout_ms, 2500)
        self.assertEqual(settings.artifact_pending_ttl_seconds, 60)

    def test_invalid_configuration_values(self) -> None:
        invalid_envs = [
            {"SIRCOM_PORT": "0"},
            {"SIRCOM_MAX_EXCEL_ROWS": "0"},
            {"SIRCOM_MAX_EXCEL_COLUMNS": "0"},
            {"SIRCOM_MAX_EXCEL_CELLS": "0"},
            {"SIRCOM_MAX_IMAGE_PIXELS": "0"},
            {"SIRCOM_MAX_IMAGE_WIDTH_PX": "0"},
            {"SIRCOM_MAX_IMAGE_HEIGHT_PX": "0"},
            {"SIRCOM_MAX_ACTIVE_JOBS": "0"},
            {"SIRCOM_WORKER_POLL_SECONDS": "0"},
            {"SIRCOM_WORKER_LEASE_TTL_SECONDS": "0"},
            {"SIRCOM_WORKER_HEARTBEAT_SECONDS": "0"},
            {"SIRCOM_DISK_FREE_MIN_MB": "-1"},
            {"SIRCOM_PURGE_INTERVAL_SECONDS": "0"},
            {"SIRCOM_PURGE_TRACE_RETENTION_DAYS": "0"},
            {"SIRCOM_SQLITE_BUSY_TIMEOUT_MS": "-1"},
            {"SIRCOM_ARTIFACT_PENDING_TTL_SECONDS": "0"},
            {"SIRCOM_WORKER_ENABLED": "maybe"},
            {"SIRCOM_DATA_DIR": ""},
        ]

        for env in invalid_envs:
            with self.subTest(env=env):
                with self.assertRaises(ConfigError):
                    load_settings(env)

    def test_image_pixel_limit_cannot_exceed_pillow_guard(self) -> None:
        from PIL import Image

        if Image.MAX_IMAGE_PIXELS is None:
            self.skipTest("Pillow image pixel guard is disabled in this environment.")

        with self.assertRaises(ConfigError):
            load_settings(
                {"SIRCOM_MAX_IMAGE_PIXELS": str(int(Image.MAX_IMAGE_PIXELS) + 1)}
            )


class WebSocleTest(unittest.TestCase):
    def test_health_route_is_cold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))

            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_ready_first_start_creates_sqlite_and_returns_200(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            settings = make_settings(tmp_path)
            sqlite_path = settings.sqlite_path
            self.assertFalse(sqlite_path.exists())
            client = TestClient(create_app(settings))

            response = client.get("/health/ready")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(sqlite_path.exists())
            payload = response.json()

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["code"], "SIRCOM_READY")
        self.assertEqual(
            [check["name"] for check in payload["checks"]],
            ["config", "data_dir", "sqlite", "disk"],
        )

    def test_ready_returns_503_when_data_dir_is_not_writable(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("Root can write to read-only directories.")

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            data_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
            try:
                settings = load_settings(
                    {
                        "SIRCOM_DATA_DIR": str(data_dir),
                        "SIRCOM_SQLITE_PATH": str(data_dir / "sircom.sqlite3"),
                        "SIRCOM_DISK_FREE_MIN_MB": "0",
                    }
                )
                client = TestClient(create_app(settings))

                response = client.get("/health/ready")
            finally:
                data_dir.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "SIRCOM_NOT_READY")
        self.assertEqual(
            response.json()["checks"][1]["code"], "SIRCOM_DATA_DIR_NOT_WRITABLE"
        )

    def test_ready_returns_503_when_disk_is_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp), SIRCOM_DISK_FREE_MIN_MB="5120")
            client = TestClient(create_app(settings))
            fake_usage = DiskUsage(total=10_000, used=5_000, free=5119 * 1024 * 1024)

            with patch("sircom2026.app.shutil.disk_usage", return_value=fake_usage):
                response = client.get("/health/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"][-1]["code"], "SIRCOM_DISK_FREE_LOW")

    def test_ready_returns_200_when_disk_is_at_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp), SIRCOM_DISK_FREE_MIN_MB="5120")
            client = TestClient(create_app(settings))
            fake_usage = DiskUsage(total=10_000, used=5_000, free=5120 * 1024 * 1024)

            with patch("sircom2026.app.shutil.disk_usage", return_value=fake_usage):
                response = client.get("/health/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"][-1]["code"], "SIRCOM_DISK_OK")

    def test_config_limits_do_not_expose_internal_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))

            response = client.get("/api/config/limits")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("limits", payload)
        self.assertEqual(payload["limits"]["excel"]["max_rows"], 200_000)
        self.assertEqual(payload["limits"]["excel"]["max_columns"], 256)
        self.assertEqual(payload["limits"]["excel"]["max_cells"], 5_000_000)
        self.assertEqual(payload["limits"]["images"]["max_pixels"], 80_000_000)
        self.assertEqual(payload["limits"]["images"]["max_width_px"], 20_000)
        self.assertEqual(payload["limits"]["images"]["max_height_px"], 20_000)
        serialized = str(payload)
        self.assertNotIn(str(settings.data_dir), serialized)
        self.assertNotIn(str(settings.sqlite_path), serialized)
        self.assertNotIn(settings.indesign_image_root, serialized)

    def test_config_limits_returns_500_when_configuration_is_invalid(self) -> None:
        with patch(
            "sircom2026.app.load_settings",
            side_effect=[ConfigError("bad"), load_settings({})],
        ):
            client = TestClient(create_app())

        response = client.get("/api/config/limits")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_CONFIG_INVALID")

    def test_openapi_and_docs_are_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            openapi_response = client.get("/openapi.json")
            docs_response = client.get("/docs")

        self.assertEqual(openapi_response.status_code, 200)
        self.assertIn("/health", openapi_response.json()["paths"])
        self.assertEqual(docs_response.status_code, 200)

    def test_shell_html_has_dsfr_page_structure_without_false_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('<html lang="fr">', html)
        self.assertIn('class="fr-skiplinks"', html)
        self.assertIn('<header class="fr-header" role="banner">', html)
        self.assertIn('class="fr-header__logo"', html)
        self.assertIn('class="fr-logo"', html)
        self.assertIn("République<br>Française", html)
        self.assertIn(
            'title="Accueil - Sircom - Made in France - traitements excel"', html
        )
        self.assertIn(
            '<p class="fr-header__service-title">SIRCOM - Made in France - traitements excel</p>',
            html,
        )
        self.assertIn(
            '<p class="fr-header__service-tagline">Interface de préparation au publipostage</p>',
            html,
        )
        self.assertIn('aria-controls="header-menu"', html)
        self.assertIn('id="header-menu"', html)
        self.assertIn('<nav class="fr-nav" id="header-navigation"', html)
        self.assertIn('href="/#lots-title">Lots</a>', html)
        self.assertNotIn("Workflow d'orchestration", html)
        self.assertNotIn('href="#navigation"', html)
        self.assertIn('href="#footer"', html)
        self.assertIn('<main id="contenu"', html)
        self.assertIn('<footer class="fr-footer" id="footer" role="contentinfo">', html)
        self.assertIn('class="fr-footer__brand fr-enlarge-link"', html)
        self.assertIn(
            'title="Retour à l\'accueil - Sircom 2026 - République Française"',
            html,
        )
        self.assertIn("<p>Miweb SNUM 2026, pour le SIRCOM</p>", html)
        header_html = html.split("<main", 1)[0]
        footer_html = html.split('<footer class="fr-footer" id="footer"', 1)[1]
        self.assertNotIn('href="/docs">API</a>', header_html)
        self.assertNotIn('href="/health">Santé</a>', header_html)
        self.assertNotIn(
            "https://github.com/Alexmacapple/scripts-traitement-sircom", header_html
        )
        self.assertIn('href="/docs">API</a>', footer_html)
        self.assertIn('href="/health">Santé</a>', footer_html)
        self.assertIn(
            'href="https://github.com/Alexmacapple/scripts-traitement-sircom">Dépôt Git</a>',
            footer_html,
        )
        self.assertNotIn('class="fr-footer__bottom"', html)
        self.assertNotIn("Plan du site", html)
        self.assertNotIn("Accessibilité : non auditée", html)
        self.assertNotIn("Mentions légales", html)
        self.assertNotIn("Données personnelles", html)
        self.assertNotIn("Gestion des cookies", html)
        self.assertNotIn(
            "Application locale. Contenus et mentions à finaliser avant publication.",
            html,
        )
        self.assertIn("/static/dsfr/1.14.4/dsfr.min.css", html)
        self.assertIn("/static/dsfr/1.14.4/utility/icons/icons.min.css", html)
        self.assertIn("/static/dsfr/1.14.4/dsfr.module.min.js", html)
        self.assertRegex(html, r"/static/sircom\.css\?v=\d+")
        self.assertRegex(html, r"/static/app\.js\?v=\d+")
        self.assertIn('class="fr-callout fr-icon-info-line"', html)
        self.assertNotIn("fr-icon-information-line", html)
        self.assertNotIn("cdn.jsdelivr.net", html)
        self.assertNotIn('href="#"', html)
        self.assertNotIn("conforme RGAA", html)

    def test_shell_html_has_valid_local_references_and_popup_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        parser = ShellHtmlParser()
        parser.feed(response.text)

        labelledby_violations = []
        disallowed_generic_roles = {
            "",
            "caption",
            "code",
            "deletion",
            "emphasis",
            "generic",
            "insertion",
            "paragraph",
            "presentation",
            "strong",
            "subscript",
            "superscript",
        }
        for element in parser.elements:
            role = element.attrs.get("role", "")
            classes = set(element.attrs.get("class", "").split())
            if (
                element.tag == "div"
                and "aria-labelledby" in element.attrs
                and "fr-header__menu" not in classes
                and role in disallowed_generic_roles
            ):
                labelledby_violations.append(element.attrs)
        self.assertEqual(labelledby_violations, [])

        missing_controls = [
            element.attrs
            for element in parser.elements
            if element.attrs.get("aria-controls")
            and element.attrs["aria-controls"] not in parser.elements_by_id
        ]
        missing_labelledby = [
            element.attrs
            for element in parser.elements
            for ref in element.attrs.get("aria-labelledby", "").split()
            if ref and ref not in parser.elements_by_id
        ]
        missing_anchors = [
            anchor
            for anchor in parser.anchor_refs
            if anchor not in parser.elements_by_id
        ]

        self.assertEqual(missing_controls, [])
        self.assertEqual(missing_labelledby, [])
        self.assertEqual(missing_anchors, [])

        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            missing_assets = [
                path
                for path in parser.asset_paths
                if client.get(path).status_code != 200
            ]
        self.assertEqual(missing_assets, [])

    def test_lot_step_buttons_have_visible_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot boutons"}).json()[
                "lot"
            ]["id"]

            response = client.get(f"/?lot_id={lot_id}")

        self.assertEqual(response.status_code, 200)
        parser = ShellHtmlParser()
        parser.feed(response.text)
        unlabeled_buttons = [
            attrs
            for attrs, text in parser.buttons
            if not re.sub(r"\s+", " ", text).strip()
        ]
        self.assertEqual(unlabeled_buttons, [])

    def test_footer_information_links_return_dsfr_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            responses = {
                path: client.get(path)
                for path in (
                    "/plan-du-site",
                    "/accessibilite",
                    "/mentions-legales",
                    "/donnees-personnelles",
                    "/gestion-cookies",
                )
            }

        for path, response in responses.items():
            with self.subTest(path=path):
                self.assertEqual(response.status_code, 200)
                self.assertIn('<html lang="fr">', response.text)
                self.assertIn('<header class="fr-header" role="banner">', response.text)
                self.assertIn(
                    '<footer class="fr-footer" id="footer" role="contentinfo">',
                    response.text,
                )
                self.assertIn('href="/docs">API</a>', response.text)
                self.assertIn('href="/health">Santé</a>', response.text)
                self.assertNotIn('href="#"', response.text)
                self.assertNotIn("conforme RGAA", response.text)

    def test_local_dsfr_static_assets_are_served(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            css_response = client.get("/static/dsfr/1.14.4/dsfr.min.css")
            icons_response = client.get(
                "/static/dsfr/1.14.4/utility/icons/icons.min.css"
            )
            js_response = client.get("/static/dsfr/1.14.4/dsfr.module.min.js")

        self.assertEqual(css_response.status_code, 200)
        self.assertIn("fr-header", css_response.text)
        self.assertEqual(icons_response.status_code, 200)
        self.assertIn("fr-icon-info-line", icons_response.text)
        self.assertEqual(js_response.status_code, 200)

    def test_local_dsfr_css_references_existing_assets(self) -> None:
        dsfr_root = (
            Path(__file__).parents[1] / "sircom2026" / "static" / "dsfr" / "1.14.4"
        )
        css_files = [
            dsfr_root / "dsfr.min.css",
            dsfr_root / "utility" / "icons" / "icons.min.css",
        ]
        missing_paths = []

        for css_file in css_files:
            css = css_file.read_text(encoding="utf-8")
            referenced_paths = set()
            for match in re.finditer(r"url\(([^)]+)\)", css):
                raw_url = match.group(1).strip().strip("\"'")
                if raw_url.startswith("data:") or "://" in raw_url:
                    continue
                referenced_paths.add(raw_url)
            missing_paths.extend(
                f"{css_file.relative_to(dsfr_root)} -> {path}"
                for path in referenced_paths
                if not (css_file.parent / path).exists()
            )

        self.assertIn(
            "fr--info-line.svg",
            (dsfr_root / "utility" / "icons" / "icons.min.css").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(missing_paths, [])


if __name__ == "__main__":
    unittest.main()
