from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sircom2026.database import Database, PROBLEM_SEVERITIES, STEP_STATUSES
from sircom2026.lots import STEP_STATUS_LABELS, create_lot_with_steps, get_lot_detail
from sircom2026.state import (
    StateTransitionError,
    block_step,
    cancel_active_step,
    complete_step,
    fail_step,
    record_problem,
    require_human_validation,
)


class BusinessStateTest(unittest.TestCase):
    def test_statuses_and_problem_severities_are_stable_and_displayed_in_french(self) -> None:
        self.assertTrue(
            {
                "non_demarre",
                "pret",
                "en_cours",
                "action_requise",
                "bloque",
                "termine",
                "termine_avec_alertes",
                "echoue",
                "ignore",
                "annule",
            }.issubset(set(STEP_STATUSES))
        )
        self.assertEqual(set(PROBLEM_SEVERITIES), {"bloquant", "alerte", "information"})
        self.assertEqual(STEP_STATUS_LABELS["action_requise"], "Action requise")
        self.assertEqual(STEP_STATUS_LABELS["termine_avec_alertes"], "Terminée avec alertes")

    def test_complete_step_without_warning_marks_termine_and_persists_event_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot etat")
                step = complete_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                )
                detail = get_lot_detail(repositories, lot["id"])

                event_types = [
                    row["event_type"]
                    for row in repositories.events.list_for_lot(lot["id"], limit=10)
                ]

            self.assertEqual(step["status"], "termine")
            self.assertIsNotNone(step["finished_at"])
            self.assertEqual(detail["status"], "en_cours")
            self.assertIn("step.completed", event_types)
            self.assertEqual(detail["problems"], [])

    def test_open_alert_requires_termine_avec_alertes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot alerte")
                problem = record_problem(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    run_id="run_diag_1",
                    severity="alerte",
                    code="SIRCOM_EXCEL_HIDDEN_COLUMNS",
                    title="Colonnes masquées détectées",
                    cause="Le classeur contient une colonne masquée dans un onglet utile.",
                    action="Afficher ou supprimer la colonne, puis relancer le diagnostic.",
                    location={"onglet": "Produits", "colonne": "C"},
                    technical={
                        "hidden_columns": 1,
                        "relative_path": "lots/lot_1/source.xlsx",
                        "siret": "12345678900000",
                        "nested": {"path": "/private/tmp/source.xlsx"},
                    },
                )
                step_before = repositories.steps.get_by_lot_key(lot["id"], "diagnostic_excel")
                if step_before is None:
                    self.fail("Expected diagnostic_excel step to exist.")

                with self.assertRaises(ValueError):
                    repositories.steps.update_status(step_before["id"], "termine")

                with self.assertRaises(StateTransitionError):
                    complete_step(
                        repositories,
                        lot_id=lot["id"],
                        step_key="diagnostic_excel",
                        run_id="run_diag_1",
                    )

                step = complete_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    run_id="run_diag_1",
                    with_warnings=True,
                )
                detail = get_lot_detail(repositories, lot["id"])

            self.assertEqual(step["status"], "termine_avec_alertes")
            self.assertEqual(detail["counters"]["problems_open_count"], 1)
            self.assertEqual(problem["cause"], "Le classeur contient une colonne masquée dans un onglet utile.")
            self.assertEqual(problem["action"], "Afficher ou supprimer la colonne, puis relancer le diagnostic.")
            self.assertEqual(detail["problem_groups"]["alerte"]["items"][0]["code"], "SIRCOM_EXCEL_HIDDEN_COLUMNS")
            self.assertEqual(
                detail["problem_groups"]["alerte"]["items"][0]["location_label"],
                "Onglet Produits, Colonne C",
            )
            self.assertEqual(
                detail["problem_groups"]["alerte"]["items"][0]["technical"],
                {"hidden_columns": 1},
            )

    def test_human_validation_sets_step_and_lot_to_action_requise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot validation")
                step = require_human_validation(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    run_id="run_mapping_1",
                )
                refreshed_lot = repositories.lots.get_required(lot["id"])

            self.assertEqual(step["status"], "action_requise")
            self.assertEqual(refreshed_lot["status"], "action_requise")

    def test_block_step_records_open_bloquant_problem_and_lot_bloque(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot bloque")
                step = block_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="fusion_multi_onglets",
                    run_id="run_fusion_1",
                    code="SIRCOM_ID_DOSSIER_DUPLICATE",
                    title="Doublons id_dossier",
                    cause="La fusion detecte plusieurs lignes pour le meme id_dossier.",
                    action="Corriger les doublons dans l'Excel source, puis relancer la fusion.",
                    location={"onglet": "Candidatures"},
                    technical={"duplicates_count": 2},
                )
                refreshed_lot = repositories.lots.get_required(lot["id"])
                problems = repositories.problems.list_for_lot(lot["id"])

            self.assertEqual(step["status"], "bloque")
            self.assertEqual(refreshed_lot["status"], "bloque")
            self.assertEqual(len(problems), 1)
            self.assertEqual(problems[0]["severity"], "bloquant")

    def test_fail_step_records_problem_and_lot_echoue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot echec")
                step = fail_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    run_id="run_norm_1",
                    code="SIRCOM_UNEXPECTED_ERROR",
                    title="Erreur technique inattendue",
                    cause="La normalisation s'est interrompue sur une erreur non prévue.",
                    action="Consulter le journal technique, corriger la cause puis relancer l'etape.",
                    technical={"error_code": "ValueError"},
                )
                refreshed_lot = repositories.lots.get_required(lot["id"])
                problem = repositories.problems.list_for_lot(lot["id"])[0]

            self.assertEqual(step["status"], "echoue")
            self.assertEqual(refreshed_lot["status"], "echoue")
            self.assertEqual(problem["code"], "SIRCOM_UNEXPECTED_ERROR")

    def test_problem_run_id_must_match_current_step_run_when_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot run mismatch")
                step = repositories.steps.get_by_lot_key(lot["id"], "rapports")
                if step is None:
                    self.fail("Expected rapports step to exist.")
                repositories.steps.update_status(step["id"], "en_cours", run_id="run_current")

                with self.assertRaises(ValueError):
                    record_problem(
                        repositories,
                        lot_id=lot["id"],
                        step_key="rapports",
                        run_id="run_old",
                        severity="bloquant",
                        code="SIRCOM_RUN_MISMATCH",
                        title="Run incohérent",
                        cause="Le run ne correspond plus à l'étape courante.",
                        action="Ignorer l'écriture tardive et relancer si nécessaire.",
                    )

    def test_cancel_active_step_marks_step_job_and_lot_annule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot annule")
                job = repositories.jobs.create(
                    lot_id=lot["id"],
                    step_key="upload_images",
                    run_id="run_images_1",
                    idempotency_key="upload_images:run_images_1",
                    status="running",
                )
                repositories.steps.update_status(
                    repositories.steps.get_by_lot_key(lot["id"], "upload_images")["id"],
                    "en_cours",
                    run_id="run_images_1",
                )

                step = cancel_active_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_images",
                    run_id="run_images_1",
                )
                refreshed_lot = repositories.lots.get_required(lot["id"])
                refreshed_job = repositories.jobs.get_required(job["id"])

            self.assertEqual(step["status"], "annule")
            self.assertEqual(refreshed_lot["status"], "annule")
            self.assertEqual(refreshed_job["status"], "canceled")
            self.assertIsNotNone(refreshed_job["cancel_requested_at"])
            self.assertIsNotNone(refreshed_job["finished_at"])

    def test_events_and_problems_remain_separate_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot separation")
                record_problem(
                    repositories,
                    lot_id=lot["id"],
                    step_key="previsualisation_csv",
                    severity="information",
                    code="SIRCOM_PREVIEW_READY",
                    title="Aperçu disponible",
                    cause="Un aperçu CSV a été produit pour validation.",
                    action="Vérifier l'aperçu dans l'interface.",
                    technical={"rows_count": 9},
                )
                repositories.events.create(
                    lot_id=lot["id"],
                    step_key="package_final",
                    run_id="run_package_1",
                    level="warning",
                    event_type="artifact.commit_rejected",
                    payload={
                        "code": "SIRCOM_ARTIFACT_COMMIT_REJECTED",
                        "run_id": "run_package_1",
                        "step_key": "package_final",
                    },
                )
                event_rows = repositories.connection.execute(
                    "SELECT event_type, payload_json FROM evenements WHERE event_type = ?",
                    ("problem.recorded",),
                ).fetchall()
                problem_rows = repositories.connection.execute(
                    "SELECT code, technical_json FROM problemes WHERE lot_id = ?",
                    (lot["id"],),
                ).fetchall()
                detail = get_lot_detail(repositories, lot["id"])

            self.assertEqual(len(event_rows), 1)
            self.assertEqual(len(problem_rows), 1)
            self.assertEqual(problem_rows[0]["code"], "SIRCOM_PREVIEW_READY")
            self.assertEqual(json.loads(event_rows[0]["payload_json"])["code"], "SIRCOM_PREVIEW_READY")
            self.assertIn(
                "Commit d'artefact refusé",
                {event["label"] for event in detail["events"]},
            )


def migrated_database(tmp: str) -> Database:
    database = Database(Path(tmp) / "sircom.sqlite3")
    database.migrate()
    return database


if __name__ == "__main__":
    unittest.main()
