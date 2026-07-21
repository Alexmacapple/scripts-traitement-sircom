from __future__ import annotations

import os
import re
import stat
import tempfile
import unittest
from dataclasses import dataclass
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
        self.assertEqual(settings.max_zip_mb, 1024)
        self.assertEqual(settings.max_image_count, 1500)
        self.assertEqual(settings.max_image_mb, 50)
        self.assertEqual(settings.max_unzipped_mb, 3072)
        self.assertEqual(settings.indesign_image_root, "/Users/victoria/Documents/export-jpg-resize")
        self.assertEqual(settings.bind_host, "127.0.0.1")
        self.assertEqual(settings.port, 8000)
        self.assertTrue(settings.worker_enabled)
        self.assertEqual(settings.worker_id, "local-1")
        self.assertEqual(settings.max_active_jobs, 1)
        self.assertEqual(settings.disk_free_min_mb, 5120)

    def test_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "SIRCOM_DATA_DIR": str(Path(tmp) / "custom-data"),
                "SIRCOM_SQLITE_PATH": str(Path(tmp) / "custom.sqlite3"),
                "SIRCOM_RETENTION_DAYS": "14",
                "SIRCOM_MAX_EXCEL_MB": "12",
                "SIRCOM_MAX_ZIP_MB": "99",
                "SIRCOM_MAX_IMAGE_COUNT": "42",
                "SIRCOM_MAX_IMAGE_MB": "8",
                "SIRCOM_MAX_UNZIPPED_MB": "256",
                "SIRCOM_INDESIGN_IMAGE_ROOT": "/tmp/export-jpg-resize",
                "SIRCOM_BIND_HOST": "0.0.0.0",
                "SIRCOM_PORT": "9000",
                "SIRCOM_WORKER_ENABLED": "false",
                "SIRCOM_WORKER_ID": "worker-test",
                "SIRCOM_MAX_ACTIVE_JOBS": "2",
                "SIRCOM_DISK_FREE_MIN_MB": "128",
            }

            settings = load_settings(env)

        self.assertEqual(settings.data_dir.name, "custom-data")
        self.assertEqual(settings.sqlite_path.name, "custom.sqlite3")
        self.assertEqual(settings.retention_days, 14)
        self.assertEqual(settings.max_excel_mb, 12)
        self.assertEqual(settings.max_zip_mb, 99)
        self.assertEqual(settings.max_image_count, 42)
        self.assertEqual(settings.max_image_mb, 8)
        self.assertEqual(settings.max_unzipped_mb, 256)
        self.assertEqual(settings.indesign_image_root, "/tmp/export-jpg-resize")
        self.assertEqual(settings.bind_host, "0.0.0.0")
        self.assertEqual(settings.port, 9000)
        self.assertFalse(settings.worker_enabled)
        self.assertEqual(settings.worker_id, "worker-test")
        self.assertEqual(settings.max_active_jobs, 2)
        self.assertEqual(settings.disk_free_min_mb, 128)

    def test_invalid_configuration_values(self) -> None:
        invalid_envs = [
            {"SIRCOM_PORT": "0"},
            {"SIRCOM_MAX_ACTIVE_JOBS": "0"},
            {"SIRCOM_DISK_FREE_MIN_MB": "-1"},
            {"SIRCOM_WORKER_ENABLED": "maybe"},
            {"SIRCOM_DATA_DIR": ""},
        ]

        for env in invalid_envs:
            with self.subTest(env=env):
                with self.assertRaises(ConfigError):
                    load_settings(env)


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
        self.assertEqual(response.json()["checks"][1]["code"], "SIRCOM_DATA_DIR_NOT_WRITABLE")

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
        self.assertIn("limits", payload)
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
        self.assertEqual(response.json()["detail"]["code"], "SIRCOM_CONFIG_INVALID")

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
        self.assertIn('id="header-menu-button"', html)
        self.assertIn('aria-controls="header-menu"', html)
        self.assertIn('class="fr-btn--close fr-btn"', html)
        self.assertIn('<main id="contenu"', html)
        self.assertIn('<footer class="fr-footer" role="contentinfo">', html)
        self.assertIn('class="fr-footer__bottom"', html)
        self.assertIn("Accessibilité : non auditée", html)
        self.assertIn("/static/dsfr/1.14.4/dsfr.min.css", html)
        self.assertIn("/static/dsfr/1.14.4/utility/icons/icons.min.css", html)
        self.assertIn("/static/dsfr/1.14.4/dsfr.module.min.js", html)
        self.assertIn('class="fr-callout fr-icon-info-line"', html)
        self.assertNotIn("fr-icon-information-line", html)
        self.assertNotIn("cdn.jsdelivr.net", html)
        self.assertNotIn('href="#"', html)
        self.assertNotIn("conforme RGAA", html)

    def test_local_dsfr_static_assets_are_served(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            css_response = client.get("/static/dsfr/1.14.4/dsfr.min.css")
            icons_response = client.get("/static/dsfr/1.14.4/utility/icons/icons.min.css")
            js_response = client.get("/static/dsfr/1.14.4/dsfr.module.min.js")

        self.assertEqual(css_response.status_code, 200)
        self.assertIn("fr-header", css_response.text)
        self.assertEqual(icons_response.status_code, 200)
        self.assertIn("fr-icon-info-line", icons_response.text)
        self.assertEqual(js_response.status_code, 200)

    def test_local_dsfr_css_references_existing_assets(self) -> None:
        dsfr_root = Path(__file__).parents[1] / "sircom2026" / "static" / "dsfr" / "1.14.4"
        css_files = [dsfr_root / "dsfr.min.css", dsfr_root / "utility" / "icons" / "icons.min.css"]
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
            (dsfr_root / "utility" / "icons" / "icons.min.css").read_text(encoding="utf-8"),
        )
        self.assertEqual(missing_paths, [])


if __name__ == "__main__":
    unittest.main()
