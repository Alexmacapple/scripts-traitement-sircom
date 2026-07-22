from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from sircom2026._database_lots import LotsRepository
from sircom2026._database_steps import StepsRepository
from sircom2026._database_shared import (
    LOT_WRITE_BLOCKED_STATUSES,
    PROBLEM_SEVERITIES,
    PROBLEM_STATUSES,
    _fetch_one,
    _json,
    _new_id,
    _now,
    _placeholders,
    _validate_choice,
)

__all__ = ['ProblemsRepository']


class ProblemsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        severity: str,
        code: str,
        title: str,
        message: str,
        cause: str | None = None,
        action: str | None = None,
        run_id: str | None = None,
        location: Mapping[str, Any] | None = None,
        technical: Mapping[str, Any] | None = None,
        problem_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("problem severity", severity, PROBLEM_SEVERITIES)
        self._validate_write_allowed(lot_id=lot_id, step_key=step_key, run_id=run_id)
        now = _now()
        row_id = problem_id or _new_id("problem")
        cause_text = cause if cause is not None else message
        action_text = action if action is not None else "Corriger la cause puis relancer l'étape concernée."
        self.connection.execute(
            """
            INSERT INTO problemes (
                id, created_at, updated_at, lot_id, step_key, run_id, severity,
                code, title, cause, message, action, location_json,
                technical_json, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                lot_id,
                step_key,
                run_id,
                severity,
                code,
                title,
                cause_text,
                message,
                action_text,
                _json(location or {}),
                _json(technical or {}),
                "open",
            ),
        )
        LotsRepository(self.connection).refresh_problem_counters(lot_id)
        return self.get_required(row_id)

    def get(self, problem_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM problemes WHERE id = ?", (problem_id,))

    def get_required(self, problem_id: str) -> dict[str, Any]:
        row = self.get(problem_id)
        if row is None:
            raise KeyError(problem_id)
        return row

    def update_status(self, problem_id: str, status: str) -> dict[str, Any]:
        _validate_choice("problem status", status, PROBLEM_STATUSES)
        problem = self.get_required(problem_id)
        now = _now()
        resolved_at = now if status == "resolved" else None
        self.connection.execute(
            """
            UPDATE problemes
            SET status = ?, resolved_at = COALESCE(?, resolved_at), updated_at = ?
            WHERE id = ?
            """,
            (status, resolved_at, now, problem_id),
        )
        LotsRepository(self.connection).refresh_problem_counters(problem["lot_id"])
        return self.get_required(problem_id)

    def _validate_write_allowed(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str | None,
    ) -> None:
        lot = LotsRepository(self.connection).get_required(lot_id)
        if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot record a problem for a canceled or deleted lot.")
        step = StepsRepository(self.connection).get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        current_run_id = step["current_run_id"]
        if run_id is not None and current_run_id is not None and current_run_id != run_id:
            raise ValueError("Problem run_id does not match the current step run_id.")

    def list_for_lot(
        self,
        lot_id: str,
        *,
        include_resolved: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        status_filter = "" if include_resolved else "AND status = 'open'"
        rows = self.connection.execute(
            f"""
            SELECT * FROM problemes
            WHERE lot_id = ?
              {status_filter}
            ORDER BY
                CASE severity
                    WHEN 'bloquant' THEN 0
                    WHEN 'alerte' THEN 1
                    ELSE 2
                END,
                created_at DESC,
                id DESC
            LIMIT ?
            """,
            (lot_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def count_open_for_step_by_severity(
        self,
        *,
        lot_id: str,
        step_key: str,
        severity: str,
    ) -> int:
        _validate_choice("problem severity", severity, PROBLEM_SEVERITIES)
        row = self.connection.execute(
            """
            SELECT COUNT(*) FROM problemes
            WHERE lot_id = ?
              AND step_key = ?
              AND severity = ?
              AND status = 'open'
            """,
            (lot_id, step_key, severity),
        ).fetchone()
        return int(row[0])

    def count_open_by_severity(self, *, lot_id: str, severity: str) -> int:
        _validate_choice("problem severity", severity, PROBLEM_SEVERITIES)
        row = self.connection.execute(
            """
            SELECT COUNT(*) FROM problemes
            WHERE lot_id = ?
              AND severity = ?
              AND status = 'open'
            """,
            (lot_id, severity),
        ).fetchone()
        return int(row[0])

    def mark_open_obsolete_for_steps(self, *, lot_id: str, step_keys: tuple[str, ...]) -> int:
        if not step_keys:
            return 0
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE problemes
            SET status = 'obsolete', updated_at = ?
            WHERE lot_id = ?
              AND step_key IN ({_placeholders(len(step_keys))})
              AND status = 'open'
            """,
            (now, lot_id, *step_keys),
        )
        LotsRepository(self.connection).refresh_problem_counters(lot_id)
        return cursor.rowcount
