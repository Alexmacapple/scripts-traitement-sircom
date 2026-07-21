from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from openpyxl import Workbook

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.synthetic_excels import create_synthetic_excels
from sircom2026.worker_runner import run_worker_once


def make_settings(tmpdir: Path):
    return load_settings(
        {
            "SIRCOM_DATA_DIR": str(tmpdir / "data"),
            "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
            "SIRCOM_DISK_FREE_MIN_MB": "0",
        }
    )


def excel_file(path: Path) -> dict[str, tuple[str, bytes, str]]:
    return {
        "file": (
            path.name,
            path.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def prepare_importable_lot(
    client: TestClient,
    settings,
    excel_path: Path,
    *,
    title: str,
    key: str,
) -> str:
    lot_id = client.post("/api/lots", json={"title": title}).json()["lot"]["id"]
    upload = client.post(
        f"/api/lots/{lot_id}/excel",
        files=excel_file(excel_path),
        headers={"X-Idempotency-Key": f"upload-{key}"},
    )
    worker_result = run_worker_once(settings=settings)

    if upload.status_code != 202:
        raise AssertionError(upload.text)
    if worker_result.outcome != "succeeded":
        raise AssertionError(worker_result)
    return lot_id


class MappingApiTest(unittest.TestCase):
    def test_default_mapping_selects_useful_columns_and_keeps_structural_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["valid_multi_tabs"])
            client = TestClient(create_app(settings))
            lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["valid_multi_tabs"],
                title="Lot mapping",
                key="mapping-default",
            )

            response = client.get(f"/api/lots/{lot_id}/mapping")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        mapping = payload["mapping"]
        columns = mapping["columns"]
        self.assertEqual(mapping["source"], "default")
        self.assertEqual(mapping["rules_version"], "mapping-v1")
        self.assertEqual(len(mapping["structural_fingerprint"]), 64)
        self.assertNotIn("Objet de test", str(payload))
        self.assertNotIn(str(tmpdir), str(payload))

        source_columns = [column for column in columns if not column["system"]]
        self.assertEqual(len(source_columns), 16)
        self.assertTrue(
            all(
                column["source_sheet"]
                and column["source_column_letter"]
                and column["source_header"]
                for column in source_columns
            )
        )

        exported_csv_names = [
            column["csv_name"]
            for column in columns
            if column["status"] == "exporte"
        ]
        self.assertEqual(exported_csv_names.count("id_dossier"), 1)
        id_position = exported_csv_names.index("id_dossier")
        self.assertEqual(exported_csv_names[id_position + 1 : id_position + 3], ["imageid", "@pathimg"])
        self.assertIn("d_nomdupro", exported_csv_names)
        self.assertIn("b_region", exported_csv_names)
        self.assertIn("g_datedede", exported_csv_names)

        duplicate_id_columns = [
            column
            for column in columns
            if column["logical_role"] == "id_dossier" and column["status"] == "supprime"
        ]
        self.assertEqual(len(duplicate_id_columns), 2)
        self.assertTrue(all(column["suppression_reason"] for column in duplicate_id_columns))

    def test_mapping_draft_validation_and_profile_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["valid_multi_tabs"])
            client = TestClient(create_app(settings))
            lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["valid_multi_tabs"],
                title="Lot mapping validation",
                key="mapping-validation",
            )
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            product_column = find_column(mapping, "Dossiers", "D", "Nom du produit")
            product_column["csv_name"] = "d_produit"

            draft = client.post(
                f"/api/lots/{lot_id}/mapping/draft",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "mapping-draft-1"},
            )
            validate = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "mapping-validate-1"},
            )
            validate_replay = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "mapping-validate-1"},
            )
            product_column["csv_name"] = "d_autre"
            validate_reused_key = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "mapping-validate-1"},
            )
            profile = client.post(
                f"/api/lots/{lot_id}/mapping/profile",
                json={"name": "Profil Sircom test"},
            )
            detail = client.get(f"/api/lots/{lot_id}").json()["lot"]
            validated_mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]

        self.assertEqual(draft.status_code, 200, draft.text)
        self.assertEqual(draft.json()["mapping"]["source"], "draft")
        self.assertEqual(step_status(draft.json()["lot"], "mapping"), "action_requise")
        self.assertEqual(validate.status_code, 200, validate.text)
        self.assertEqual(validate.json()["mapping"]["source"], "validated")
        self.assertIn("fusion_multi_onglets", validate.json()["invalidated_steps"])
        self.assertEqual(validate_replay.status_code, 200, validate_replay.text)
        self.assertEqual(validate_replay.json()["invalidated_steps"], [])
        self.assertEqual(
            validate_replay.json()["artifact"]["id"],
            validate.json()["artifact"]["id"],
        )
        self.assertEqual(validate_reused_key.status_code, 409)
        self.assertEqual(
            validate_reused_key.json()["error"]["code"],
            "SIRCOM_MAPPING_IDEMPOTENCY_REUSED",
        )
        self.assertEqual(step_status(detail, "mapping"), "termine")
        self.assertEqual(validated_mapping["columns"][product_column["output_position"] - 1]["csv_name"], "d_produit")

        self.assertEqual(profile.status_code, 201, profile.text)
        saved_profile = profile.json()["profile"]
        self.assertEqual(saved_profile["version"], 1)
        self.assertEqual(saved_profile["structural_fingerprint"], mapping["structural_fingerprint"])
        self.assertEqual(saved_profile["sheets"], mapping["sheets"])
        self.assertTrue(saved_profile["headers"])
        self.assertTrue(saved_profile["letters"])
        self.assertTrue(saved_profile["logical_roles"])
        self.assertTrue(saved_profile["last_used_at"])
        self.assertNotIn("Objet de test", str(saved_profile))
        self.assertNotIn(str(tmpdir), str(saved_profile))

    def test_compatible_profile_is_only_applied_as_draft_after_user_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["valid_multi_tabs"])
            client = TestClient(create_app(settings))
            first_lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["valid_multi_tabs"],
                title="Lot profil source",
                key="profile-source",
            )
            first_mapping = client.get(f"/api/lots/{first_lot_id}/mapping").json()["mapping"]
            find_column(first_mapping, "Dossiers", "D", "Nom du produit")["csv_name"] = "d_produit"
            validate = client.post(
                f"/api/lots/{first_lot_id}/mapping/validate",
                json=mapping_submission(first_mapping),
                headers={"X-Idempotency-Key": "profile-source-validate"},
            )
            profile = client.post(
                f"/api/lots/{first_lot_id}/mapping/profile",
                json={"name": "Profil compatible"},
            ).json()["profile"]

            second_lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["valid_multi_tabs"],
                title="Lot profil cible",
                key="profile-target",
            )
            before_apply = client.get(f"/api/lots/{second_lot_id}/mapping").json()
            apply_profile = client.post(
                f"/api/lots/{second_lot_id}/mapping/profile-draft",
                json={"profile_id": profile["id"]},
                headers={"X-Idempotency-Key": "profile-target-draft"},
            )
            after_apply = client.get(f"/api/lots/{second_lot_id}/mapping").json()

        self.assertEqual(validate.status_code, 200, validate.text)
        self.assertEqual(before_apply["mapping"]["source"], "default")
        self.assertEqual(
            find_column(before_apply["mapping"], "Dossiers", "D", "Nom du produit")["csv_name"],
            "d_nomdupro",
        )
        self.assertEqual(len(before_apply["profiles"]["compatible"]), 1)
        self.assertEqual(before_apply["profiles"]["compatible"][0]["id"], profile["id"])
        self.assertEqual(apply_profile.status_code, 200, apply_profile.text)
        self.assertEqual(after_apply["mapping"]["source"], "profile_draft")
        self.assertEqual(step_status(apply_profile.json()["lot"], "mapping"), "action_requise")
        self.assertEqual(
            find_column(after_apply["mapping"], "Dossiers", "D", "Nom du produit")["csv_name"],
            "d_produit",
        )

    def test_incompatible_profile_is_reported_and_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(
                tmpdir / "fixtures",
                ["valid_multi_tabs", "duplicate_source_headers"],
            )
            client = TestClient(create_app(settings))
            source_lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["valid_multi_tabs"],
                title="Lot profil incompatible source",
                key="profile-incompatible-source",
            )
            source_mapping = client.get(f"/api/lots/{source_lot_id}/mapping").json()["mapping"]
            client.post(
                f"/api/lots/{source_lot_id}/mapping/validate",
                json=mapping_submission(source_mapping),
                headers={"X-Idempotency-Key": "profile-incompatible-validate"},
            )
            profile = client.post(
                f"/api/lots/{source_lot_id}/mapping/profile",
                json={"name": "Profil incompatible"},
            ).json()["profile"]
            target_lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["duplicate_source_headers"],
                title="Lot profil incompatible cible",
                key="profile-incompatible-target",
            )

            profile_view = client.get(f"/api/lots/{target_lot_id}/mapping").json()["profiles"]
            apply_profile = client.post(
                f"/api/lots/{target_lot_id}/mapping/profile-draft",
                json={"profile_id": profile["id"]},
                headers={"X-Idempotency-Key": "profile-incompatible-draft"},
            )

        self.assertEqual(len(profile_view["compatible"]), 0)
        self.assertEqual(len(profile_view["incompatible"]), 1)
        self.assertEqual(profile_view["incompatible"][0]["id"], profile["id"])
        self.assertEqual(apply_profile.status_code, 409)
        self.assertEqual(
            apply_profile.json()["error"]["code"],
            "SIRCOM_MAPPING_PROFILE_INCOMPATIBLE",
        )

    def test_validation_blocks_collisions_and_default_cleaning_handles_accents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "accent.xlsx"
            workbook_path.parent.mkdir(parents=True, exist_ok=True)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Dossiers"
            sheet.append(["id_dossier", "Élégance supérieure longue", "Region"])
            sheet.append(["ACC-001", "valeur", "Occitanie"])
            complement = workbook.create_sheet("Complement")
            complement.append(["id_dossier", "Autre libellé"])
            complement.append(["ACC-001", "valeur complementaire"])
            workbook.save(workbook_path)
            workbook.close()

            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = prepare_importable_lot(
                client,
                settings,
                workbook_path,
                title="Lot collision mapping",
                key="mapping-collision",
            )
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            accented = find_column(mapping, "Dossiers", "B", "Élégance supérieure longue")
            complement_column = find_column(mapping, "Complement", "B", "Autre libellé")
            accented["csv_name"] = "Élégance supérieure longue"
            complement_column["csv_name"] = "elegancesuperieurelongue"

            response = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "mapping-collision-validate"},
            )
            lot = client.get(f"/api/lots/{lot_id}").json()["lot"]

        self.assertEqual(accented["default_csv_name"], "b_elegance")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_MAPPING_CSV_HEADER_COLLISION")
        self.assertEqual(response.json()["error"]["details"]["warning_code"], "b_elegance")
        self.assertEqual(step_status(lot, "mapping"), "bloque")
        self.assertIn(
            "SIRCOM_MAPPING_CSV_HEADER_COLLISION",
            {problem["code"] for problem in lot["problem_groups"]["bloquant"]["items"]},
        )

    def test_mapping_validation_requires_a_business_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["valid_multi_tabs"])
            client = TestClient(create_app(settings))
            lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["valid_multi_tabs"],
                title="Lot sans colonne métier",
                key="mapping-no-business",
            )
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            for column in mapping["columns"]:
                if column["system"] or column["logical_role"] == "id_dossier":
                    continue
                column["status"] = "supprime"

            response = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "mapping-no-business-validate"},
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_MAPPING_NO_BUSINESS_COLUMN")


class MappingUiTest(unittest.TestCase):
    def test_home_ui_renders_mapping_validation_screen_after_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["valid_multi_tabs"])
            client = TestClient(create_app(settings))
            lot_id = prepare_importable_lot(
                client,
                settings,
                fixtures["valid_multi_tabs"],
                title="Lot UI mapping",
                key="mapping-ui",
            )

            response = client.get(f"/?lot_id={lot_id}")

        html = response.text
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mapping", html)
        self.assertIn('id="mapping-form"', html)
        self.assertIn("Provenance", html)
        self.assertIn("Nom CSV", html)
        self.assertIn("Dossiers", html)
        self.assertIn("Nom du produit", html)
        self.assertIn("d_nomdupro", html)
        self.assertIn("Valider le mapping", html)
        self.assertIn("Sauvegarder le brouillon", html)
        self.assertIn('data-mapping-lot-id="', html)
        self.assertNotIn('href="#"', html)
        self.assertNotIn(str(tmpdir), html)


def mapping_submission(mapping: dict[str, Any]) -> dict[str, Any]:
    return {
        "structural_fingerprint": mapping["structural_fingerprint"],
        "columns": [
            {
                "id": column["id"],
                "status": column["status"],
                "csv_name": column["csv_name"],
                "logical_role": column["logical_role"],
                "suppression_reason": column["suppression_reason"],
            }
            for column in mapping["columns"]
        ],
    }


def find_column(
    mapping: dict[str, Any],
    sheet: str,
    letter: str,
    header: str,
) -> dict[str, Any]:
    for column in mapping["columns"]:
        if (
            column["source_sheet"] == sheet
            and column["source_column_letter"] == letter
            and column["source_header"] == header
        ):
            return column
    raise AssertionError(f"Missing column {sheet}!{letter}:{header}.")


def step_status(lot: dict[str, object], step_key: str) -> str:
    for step in lot["steps"]:
        if step["key"] == step_key:
            return str(step["status"])
    raise AssertionError(f"Missing step {step_key}.")


if __name__ == "__main__":
    unittest.main()
