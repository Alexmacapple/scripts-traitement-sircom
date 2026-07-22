from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from sircom2026._database_shared import (
    EVENT_LEVELS,
    _fetch_one,
    _json_technical_payload,
    _new_id,
    _now,
    _validate_choice,
)

__all__ = ['EventsRepository']


class EventsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        step_key: str | None = None,
        run_id: str | None = None,
        level: str = "info",
        event_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("event level", level, EVENT_LEVELS)
        now = _now()
        row_id = event_id or _new_id("event")
        payload_json = _json_technical_payload(payload or {})
        self.connection.execute(
            """
            INSERT INTO evenements (
                id, created_at, updated_at, lot_id, step_key, run_id, level,
                event_type, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                lot_id,
                step_key,
                run_id,
                level,
                event_type,
                payload_json,
            ),
        )
        return self.get_required(row_id)

    def get(self, event_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM evenements WHERE id = ?", (event_id,))

    def get_required(self, event_id: str) -> dict[str, Any]:
        row = self.get(event_id)
        if row is None:
            raise KeyError(event_id)
        return row

    def update_payload(
        self,
        event_id: str,
        payload: Mapping[str, Any],
        *,
        level: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        payload_json = _json_technical_payload(payload)
        if level is None:
            self.connection.execute(
                "UPDATE evenements SET payload_json = ?, updated_at = ? WHERE id = ?",
                (payload_json, now, event_id),
            )
        else:
            _validate_choice("event level", level, EVENT_LEVELS)
            self.connection.execute(
                """
                UPDATE evenements
                SET payload_json = ?, level = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload_json, level, now, event_id),
            )
        return self.get_required(event_id)

    def list_for_lot(self, lot_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM evenements
            WHERE lot_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (lot_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
