from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from sircom2026.api.security import (
    AccessAction,
    AccessDecision,
    AccessResource,
    ActorContext,
)
from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.database import Database
from sircom2026.lots import V1_STEPS
from sircom2026.state import record_problem, require_human_validation
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


@dataclass
class RecordingPolicy:
    denied_actions: set[AccessAction] = field(default_factory=set)
    decisions: list[tuple[ActorContext, AccessAction, AccessResource]] = field(default_factory=list)

    def authorize(
        self,
        actor: ActorContext,
        action: AccessAction,
        resource: AccessResource,
    ) -> AccessDecision:
        self.decisions.append((actor, action, resource))
        if action in self.denied_actions:
            return AccessDecision.deny("denied")
        return AccessDecision.allow()


class LotsApiTest(unittest.TestCase):
    def test_create_lot_initializes_v1_steps_and_records_access(self) -> None:
        policy = RecordingPolicy()
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp)), access_policy=policy))

            response = client.post("/api/lots", json={"title": "  Lot   Sircom  "})

        payload = response.json()
        lot = payload["lot"]
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["location"], f"/api/lots/{lot['id']}")
        self.assertEqual(lot["title"], "Lot Sircom")
        self.assertEqual(lot["status"], "brouillon")
        self.assertEqual(lot["status_label"], "Brouillon")
        self.assertEqual(lot["counters"]["steps_total"], len(V1_STEPS))
        self.assertEqual([step["key"] for step in lot["steps"]], [step.key for step in V1_STEPS])
        self.assertEqual({step["status"] for step in lot["steps"]}, {"non_demarre"})
        self.assertIn("Déposer l'Excel", {step["label"] for step in lot["steps"]})
        self.assertEqual(policy.decisions[0][1], AccessAction.LOT_CREATE)

    def test_create_lot_accepts_empty_body_and_idempotency_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            empty_response = client.post("/api/lots")
            first_response = client.post(
                "/api/lots",
                json={"title": "Lot idempotent"},
                headers={"X-Idempotency-Key": "idem-create-1"},
            )
            second_response = client.post(
                "/api/lots",
                json={"title": "Lot ignore"},
                headers={"X-Idempotency-Key": "idem-create-1"},
            )
            list_response = client.get("/api/lots")

        self.assertEqual(empty_response.status_code, 201)
        self.assertIsNone(empty_response.json()["lot"]["title"])
        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(
            first_response.json()["lot"]["id"],
            second_response.json()["lot"]["id"],
        )
        self.assertEqual(list_response.json()["pagination"]["total"], 2)

    def test_list_lots_excludes_deleted_by_default_and_paginates_without_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            created_ids = [
                client.post("/api/lots", json={"title": f"Lot {index}"}).json()["lot"]["id"]
                for index in range(3)
            ]
            client.delete(f"/api/lots/{created_ids[1]}")

            response = client.get("/api/lots", params={"limit": 1, "offset": 0})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["pagination"], {"limit": 1, "offset": 0, "total": 2})
        self.assertEqual(len(payload["items"]), 1)
        self.assertNotIn("steps", payload["items"][0])
        self.assertNotEqual(payload["items"][0]["status"], "supprime")

    def test_get_lot_returns_detail_and_unknown_uses_structured_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot detail"}).json()["lot"]["id"]

            response = client.get(f"/api/lots/{lot_id}")
            missing_response = client.get("/api/lots/lot_missing")

        self.assertEqual(response.status_code, 200)
        lot = response.json()["lot"]
        self.assertEqual(lot["id"], lot_id)
        self.assertEqual(lot["counters"]["artifacts_count"], 0)
        self.assertEqual(lot["steps"][0]["label"], "Déposer l'Excel")

        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["error"]["code"], "SIRCOM_LOT_NOT_FOUND")
        self.assertNotIn("lot_missing", str(missing_response.json()))

    def test_delete_lot_marks_deleted_without_purge_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot a supprimer"}).json()["lot"]["id"]

            response = client.delete(f"/api/lots/{lot_id}")
            second_response = client.delete(f"/api/lots/{lot_id}")
            list_response = client.get("/api/lots")
            detail_response = client.get(f"/api/lots/{lot_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(response.json()["lot"]["status"], "supprime")
        self.assertIsNotNone(response.json()["lot"]["deleted_at"])
        self.assertEqual(list_response.json()["items"], [])
        self.assertEqual(detail_response.json()["lot"]["status"], "supprime")

    def test_delete_lot_with_active_job_requests_cancel_and_returns_202(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot job actif"}).json()["lot"]["id"]
            database = Database(
                settings.sqlite_path,
                busy_timeout_ms=settings.sqlite_busy_timeout_ms,
            )

            with database.transaction() as repositories:
                job = repositories.jobs.create(
                    lot_id=lot_id,
                    step_key="upload_excel",
                    run_id="run_1",
                    idempotency_key="upload:1",
                    status="running",
                )

            response = client.delete(f"/api/lots/{lot_id}")

            with database.transaction() as repositories:
                updated_job = repositories.jobs.get_required(job["id"])
                with self.assertRaises(ValueError):
                    repositories.jobs.create(
                        lot_id=lot_id,
                        step_key="upload_excel",
                        run_id="run_2",
                        idempotency_key="upload:2",
                        status="queued",
                    )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["cancel_requested_jobs"], 1)
        self.assertEqual(response.json()["lot"]["status"], "supprime")
        self.assertIsNotNone(updated_job["cancel_requested_at"])

    def test_lot_routes_verify_access_policy(self) -> None:
        policy = RecordingPolicy()
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp)), access_policy=policy))
            lot_id = client.post("/api/lots", json={"title": "Lot acces"}).json()["lot"]["id"]
            policy.denied_actions.add(AccessAction.LOT_READ)

            list_response = client.get("/api/lots")
            detail_response = client.get(f"/api/lots/{lot_id}")
            policy.denied_actions.remove(AccessAction.LOT_READ)
            policy.denied_actions.add(AccessAction.LOT_DELETE)
            delete_response = client.delete(f"/api/lots/{lot_id}")
            policy.denied_actions.remove(AccessAction.LOT_DELETE)
            policy.denied_actions.add(AccessAction.LOT_READ)
            ui_response = client.get("/")

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(detail_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(ui_response.status_code, 403)
        self.assertEqual(policy.decisions[-4][1], AccessAction.LOT_READ)
        self.assertEqual(policy.decisions[-4][2], AccessResource())
        self.assertEqual(policy.decisions[-3][2].lot_id, lot_id)
        self.assertEqual(policy.decisions[-2][1], AccessAction.LOT_DELETE)
        self.assertEqual(policy.decisions[-2][2].lot_id, lot_id)
        self.assertEqual(policy.decisions[-1][1], AccessAction.LOT_READ)
        self.assertNotIn(lot_id, str(detail_response.json()))
        self.assertNotIn(lot_id, str(delete_response.json()))


class LotsUiTest(unittest.TestCase):
    def test_home_ui_renders_create_form_lot_list_and_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot UI"}).json()["lot"]["id"]

            response = client.get(f"/?lot_id={lot_id}")

        html = response.text
        self.assertEqual(response.status_code, 200)
        self.assertIn("Créer un lot", html)
        self.assertIn('label class="fr-label" for="lot-title"', html)
        self.assertIn('id="create-lot-form"', html)
        self.assertIn('href="/?lot_id=', html)
        self.assertIn("Lot UI", html)
        self.assertIn("Timeline", html)
        self.assertIn("Déposer l&#39;Excel", html)
        self.assertIn("Préparer le package final", html)
        self.assertIn('id="delete-lot-button"', html)
        self.assertIn("/static/app.js", html)
        self.assertNotIn('href="#"', html)
        self.assertNotIn(str(Path(tmp)), html)

    def test_home_ui_tolerates_steps_without_retry_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot = client.post("/api/lots", json={"title": "Lot ancien rendu"}).json()["lot"]
            lot_id = lot["id"]
            legacy_lot = client.get(f"/api/lots/{lot_id}").json()["lot"]
            legacy_lot.pop("excel_diagnostic", None)
            for step in legacy_lot["steps"]:
                step.pop("actions", None)

            with patch("sircom2026.app.get_lot_detail", return_value=legacy_lot):
                response = client.get(f"/?lot_id={lot_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Lot ancien rendu", response.text)
        self.assertIn("Timeline", response.text)
        self.assertNotIn("Diagnostic Excel", response.text)

    def test_home_ui_hides_delete_for_deleted_lot_and_structures_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot supprime"}).json()["lot"]["id"]
            client.delete(f"/api/lots/{lot_id}")

            deleted_response = client.get(f"/?lot_id={lot_id}")
            missing_response = client.get("/?lot_id=lot_missing")

        deleted_html = deleted_response.text
        self.assertEqual(deleted_response.status_code, 200)
        self.assertIn("Supprimé", deleted_html)
        self.assertNotIn('id="delete-lot-button"', deleted_html)

        missing_html = missing_response.text
        self.assertIn("Lot introuvable", missing_html)
        self.assertIn("Cause :", missing_html)
        self.assertIn("Action attendue :", missing_html)

    def test_home_ui_renders_problem_groups_and_event_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot problemes"}).json()["lot"]["id"]
            database = Database(
                settings.sqlite_path,
                busy_timeout_ms=settings.sqlite_busy_timeout_ms,
            )

            with database.transaction() as repositories:
                record_problem(
                    repositories,
                    lot_id=lot_id,
                    step_key="diagnostic_excel",
                    severity="alerte",
                    code="SIRCOM_EXCEL_HIDDEN_COLUMNS",
                    title="Colonnes masquées détectées",
                    cause="Le classeur contient une colonne masquée.",
                    action="Afficher la colonne, puis relancer le diagnostic.",
                    location={"onglet": "Produits", "colonne": "C"},
                    technical={
                        "hidden_columns": 1,
                        "relative_path": "lots/lot_1/source.xlsx",
                        "siret": "12345678900000",
                        "nested": {"path": "/private/tmp/source.xlsx"},
                    },
                )
                require_human_validation(
                    repositories,
                    lot_id=lot_id,
                    step_key="mapping",
                    run_id="run_mapping_1",
                )

            response = client.get(f"/?lot_id={lot_id}")

        html = response.text
        self.assertEqual(response.status_code, 200)
        self.assertIn("Problèmes", html)
        self.assertIn("Alerte", html)
        self.assertIn("Colonnes masquées détectées", html)
        self.assertIn("Cause :", html)
        self.assertIn("Le classeur contient une colonne masquée.", html)
        self.assertIn("Emplacement :", html)
        self.assertIn("Onglet Produits, Colonne C", html)
        self.assertIn("Action attendue :", html)
        self.assertIn("Afficher la colonne, puis relancer le diagnostic.", html)
        self.assertIn("<summary>Détails techniques</summary>", html)
        self.assertIn("hidden_columns", html)
        self.assertNotIn("relative_path", html)
        self.assertNotIn("12345678900000", html)
        self.assertNotIn("/private/tmp/source.xlsx", html)
        self.assertIn("Événements", html)
        self.assertIn("Problème enregistré", html)
        self.assertIn("Validation humaine attendue", html)
        self.assertNotIn(str(Path(tmp)), html)

    def test_home_ui_renders_excel_diagnostic_pending_state_after_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            client = TestClient(create_app(make_settings(tmpdir)))
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["valid_multi_tabs"])
            lot_id = client.post("/api/lots", json={"title": "Lot diagnostic attente"}).json()[
                "lot"
            ]["id"]

            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(fixtures["valid_multi_tabs"]),
                headers={"X-Idempotency-Key": "ui-diagnostic-pending"},
            )
            response = client.get(f"/?lot_id={lot_id}")

        html = response.text
        self.assertEqual(upload.status_code, 202)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Diagnostic Excel", html)
        self.assertIn("Diagnostic Excel en attente", html)
        self.assertIn("Le fichier Excel est déposé et le diagnostic est prêt à être lancé.", html)
        self.assertIn("Attendre la fin du traitement, puis actualiser la page.", html)
        self.assertIn("Diagnostic non disponible tant que le worker n&#39;a pas terminé.", html)
        self.assertNotIn(str(tmpdir), html)

    def test_home_ui_renders_refused_excel_diagnostic_without_hiding_other_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["multiple_blockers"])
            lot_id = client.post("/api/lots", json={"title": "Lot Excel refuse"}).json()[
                "lot"
            ]["id"]

            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(fixtures["multiple_blockers"]),
                headers={"X-Idempotency-Key": "ui-diagnostic-refused"},
            )
            worker_result = run_worker_once(settings=settings)
            response = client.get(f"/?lot_id={lot_id}")

        html = response.text
        self.assertEqual(upload.status_code, 202)
        self.assertEqual(worker_result.outcome, "succeeded")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Excel refusé", html)
        self.assertIn('class="fr-alert fr-alert--error fr-mt-2v" role="alert"', html)
        self.assertIn("La transformation est bloquée tant que les problèmes bloquants restent ouverts.", html)
        self.assertIn("Corriger le fichier Excel puis déposer une nouvelle version.", html)
        self.assertIn("Bloquant", html)
        self.assertIn("Colonne id_dossier absente", html)
        self.assertIn("Colonnes masquées détectées", html)
        self.assertIn("Formules détectées", html)
        self.assertIn("Cause :", html)
        self.assertIn("Emplacement :", html)
        self.assertIn("Action attendue :", html)
        self.assertIn("Détails techniques", html)
        self.assertIn("fr-accordions-group", html)
        self.assertNotIn("Produit formule", html)
        self.assertNotIn(str(tmpdir), html)

    def test_home_ui_renders_non_blocking_excel_alerts_and_information(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["valid_multi_tabs"])
            lot_id = client.post("/api/lots", json={"title": "Lot Excel alertes"}).json()[
                "lot"
            ]["id"]

            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(fixtures["valid_multi_tabs"]),
                headers={"X-Idempotency-Key": "ui-diagnostic-alerts"},
            )
            worker_result = run_worker_once(settings=settings)
            response = client.get(f"/?lot_id={lot_id}")

        html = response.text
        self.assertEqual(upload.status_code, 202)
        self.assertEqual(worker_result.outcome, "succeeded")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Excel importable avec alertes", html)
        self.assertIn("Vous pouvez continuer jusqu&#39;au prochain point de validation.", html)
        self.assertIn("Alerte", html)
        self.assertIn("Information", html)
        self.assertIn("Lignes sans id_dossier", html)
        self.assertIn("Onglet vide ignoré", html)
        self.assertNotIn("Excel refusé", html)
        self.assertNotIn(str(tmpdir), html)


def excel_file(path: Path) -> dict[str, tuple[str, bytes, str]]:
    return {
        "file": (
            path.name,
            path.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


if __name__ == "__main__":
    unittest.main()
