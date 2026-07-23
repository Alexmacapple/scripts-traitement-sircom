from __future__ import annotations

import fnmatch
import tomllib
import unittest
from importlib import resources
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "sircom2026"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


class PackageDataTest(unittest.TestCase):
    def test_jinja_templates_and_partials_are_declared_as_package_data(self) -> None:
        config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        package_data = config["tool"]["setuptools"]["package-data"]["sircom2026"]

        self.assertIn("templates/*.html", package_data)
        self.assertIn("templates/partials/*.html", package_data)

        packaged_paths = {
            path.relative_to(PACKAGE_ROOT).as_posix()
            for path in PACKAGE_ROOT.glob("templates/**/*.html")
            if any(
                fnmatch.fnmatchcase(path.relative_to(PACKAGE_ROOT).as_posix(), pattern)
                for pattern in package_data
            )
        }

        self.assertIn("templates/index.html", packaged_paths)
        self.assertIn("templates/info.html", packaged_paths)
        self.assertIn("templates/partials/header.html", packaged_paths)
        self.assertIn("templates/partials/workflow_view.html", packaged_paths)

    def test_representative_partials_are_accessible_as_package_resources(self) -> None:
        template_root = resources.files("sircom2026").joinpath("templates")

        self.assertTrue(template_root.joinpath("index.html").is_file())
        self.assertTrue(template_root.joinpath("partials/header.html").is_file())
        self.assertTrue(template_root.joinpath("partials/workflow_view.html").is_file())


if __name__ == "__main__":
    unittest.main()
