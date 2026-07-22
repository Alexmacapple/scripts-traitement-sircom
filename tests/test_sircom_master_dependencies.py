from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "sircom_master_script.py"


def load_master_module():
    spec = importlib.util.spec_from_file_location("sircom_master_script", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load sircom_master_script.py.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SircomMasterDependenciesTest(unittest.TestCase):
    def test_setup_installs_version_bounded_2025_requirements_file(self) -> None:
        module = load_master_module()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bin_dir = tmp_path / module.VENV_NAME / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "python").touch()
            (bin_dir / "pip").touch()
            requirements = tmp_path / module.REQUIREMENTS_2025_FILE
            requirements.write_text(
                "openpyxl>=3.1,<4\npandas>=2.2,<3\nPillow>=12,<13\n",
                encoding="utf-8",
            )
            commands: list[list[str]] = []

            def fake_run(command, **_kwargs):
                commands.append(command)
                return subprocess.CompletedProcess(command, 0, "", "")

            with (
                patch.object(
                    module.SircomMasterProcessor,
                    "setup_logging",
                    lambda processor: setattr(processor, "logger", Mock()),
                ),
                patch.object(module.os, "getcwd", return_value=str(tmp_path)),
                patch.object(module.subprocess, "run", side_effect=fake_run),
            ):
                processor = module.SircomMasterProcessor()
                self.assertTrue(processor.setup_virtual_environment())

        self.assertEqual(
            commands,
            [[str(bin_dir / "pip"), "install", "-r", str(requirements)]],
        )


if __name__ == "__main__":
    unittest.main()
