from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from sircom2026._database_lots import LotsRepository
from sircom2026._database_shared import (
    LOT_WRITE_BLOCKED_STATUSES,
    STEP_STATUSES,
    _fetch_one,
    _json,
    _new_id,
    _now,
    _validate_choice,
)

__all__ = ['StepsRepository']


class StepsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        status: str = "non_demarre",
        step_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("step status", status, STEP_STATUSES)
        now = _now()
        row_id = step_id or _new_id("step")
        self.connection.execute(
            """
            INSERT INTO etapes (id, created_at, updated_at, lot_id, step_key, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row_id, now, now, lot_id, step_key, status),
        )
        return self.get_required(row_id)

    def get(self, step_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM etapes WHERE id = ?", (step_id,))

    def get_required(self, step_id: str) -> dict[str, Any]:
        row = self.get(step_id)
        if row is None:
            raise KeyError(step_id)
        return row

    def list_for_lot(self, lot_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM etapes
            WHERE lot_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (lot_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_by_lot_key(self, lot_id: str, step_key: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM etapes WHERE lot_id = ? AND step_key = ?",
            (lot_id, step_key),
        )

    def update_status(
        self,
        step_id: str,
        status: str,
        *,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("step status", status, STEP_STATUSES)
        step = self.get_required(step_id)
        lot_status = LotsRepository(self.connection).get_required(step["lot_id"])["status"]
        if lot_status in {"supprime", "purge"} or (
            lot_status == "annule" and status != "annule"
        ):
            raise ValueError("Cannot update a step for a canceled or deleted lot.")
        if status == "termine":
            open_alerts = self.connection.execute(
                """
                SELECT COUNT(*) FROM problemes
                WHERE lot_id = ?
                  AND step_key = ?
                  AND severity = 'alerte'
                  AND status = 'open'
                """,
                (step["lot_id"], step["step_key"]),
            ).fetchone()[0]
            if int(open_alerts):
                raise ValueError(
                    "A step with an open warning must be marked termine_avec_alertes."
                )
        now = _now()
        is_started = 1 if status == "en_cours" else 0
        is_finished = 1 if status in {
            "termine",
            "termine_avec_alertes",
            "echoue",
            "ignore",
            "annule",
        } else 0
        self.connection.execute(
            """
            UPDATE etapes
            SET
                status = ?,
                current_run_id = COALESCE(?, current_run_id),
                updated_at = ?,
                started_at = CASE
                    WHEN ? THEN COALESCE(started_at, ?)
                    ELSE started_at
                END,
                finished_at = CASE
                    WHEN ? THEN COALESCE(finished_at, ?)
                    ELSE finished_at
                END
            WHERE id = ?
            """,
            (status, run_id, now, is_started, now, is_finished, now, step_id),
        )
        return self.get_required(step_id)

    def prepare_run(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        input_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot prepare a run for a canceled or deleted lot.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET
                status = 'pret',
                current_run_id = ?,
                input_fingerprint = ?,
                output_fingerprint = NULL,
                progress_current = 0,
                progress_total = 0,
                started_at = NULL,
                finished_at = NULL,
                invalidated_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (run_id, input_fingerprint, now, step["id"]),
        )
        return self.get_required(step["id"])

    def mark_invalidated(
        self,
        *,
        lot_id: str,
        step_key: str,
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot invalidate a step for a canceled or deleted lot.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET
                status = 'invalide',
                current_run_id = NULL,
                input_fingerprint = NULL,
                output_fingerprint = NULL,
                progress_current = 0,
                progress_total = 0,
                started_at = NULL,
                finished_at = NULL,
                invalidated_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, step["id"]),
        )
        return self.get_required(step["id"])

    def set_output_fingerprint(
        self,
        *,
        lot_id: str,
        step_key: str,
        output_fingerprint: str,
        input_fingerprint: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot update a fingerprint for a canceled or deleted lot.")
        current_run_id = step["current_run_id"]
        if run_id is not None and current_run_id is not None and current_run_id != run_id:
            raise ValueError("Fingerprint run_id does not match the current step run_id.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET
                current_run_id = COALESCE(?, current_run_id),
                input_fingerprint = COALESCE(?, input_fingerprint),
                output_fingerprint = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (run_id, input_fingerprint, output_fingerprint, now, step["id"]),
        )
        return self.get_required(step["id"])

    def set_summary(
        self,
        *,
        lot_id: str,
        step_key: str,
        summary: Mapping[str, Any],
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot update a step summary for a canceled or deleted lot.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET summary_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (_json(summary), now, step["id"]),
        )
        return self.get_required(step["id"])
