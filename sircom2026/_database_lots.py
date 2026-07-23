from __future__ import annotations

import sqlite3
from typing import Any

from sircom2026._database_shared import (
    LOT_STATUSES,
    _fetch_one,
    _new_id,
    _now,
    _validate_choice,
)

__all__ = ["LotsRepository"]


class LotsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        title: str | None = None,
        status: str = "brouillon",
        lot_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("lot status", status, LOT_STATUSES)
        now = _now()
        row_id = lot_id or _new_id("lot")
        self.connection.execute(
            """
            INSERT INTO lots (id, created_at, updated_at, status, title, idempotency_key)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row_id, now, now, status, title, idempotency_key),
        )
        return self.get_required(row_id)

    def get(self, lot_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM lots WHERE id = ?", (lot_id,))

    def get_required(self, lot_id: str) -> dict[str, Any]:
        row = self.get(lot_id)
        if row is None:
            raise KeyError(lot_id)
        return row

    def get_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM lots WHERE idempotency_key = ?",
            (idempotency_key,),
        )

    def list(
        self,
        *,
        include_deleted: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where = "" if include_deleted else "WHERE status NOT IN ('supprime', 'purge')"
        rows = self.connection.execute(
            f"""
            SELECT * FROM lots
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self, *, include_deleted: bool = False) -> int:
        where = "" if include_deleted else "WHERE status NOT IN ('supprime', 'purge')"
        row = self.connection.execute(f"SELECT COUNT(*) FROM lots {where}").fetchone()
        return int(row[0])

    def update_status(self, lot_id: str, status: str) -> dict[str, Any]:
        _validate_choice("lot status", status, LOT_STATUSES)
        self.connection.execute(
            "UPDATE lots SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), lot_id),
        )
        return self.get_required(lot_id)

    def request_cancel(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        self.connection.execute(
            """
            UPDATE lots
            SET cancel_requested_at = COALESCE(cancel_requested_at, ?), updated_at = ?
            WHERE id = ?
            """,
            (now, now, lot_id),
        )
        return self.get_required(lot_id)

    def mark_deleted(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        self.connection.execute(
            """
            UPDATE lots
            SET
                status = 'supprime',
                delete_requested_at = COALESCE(delete_requested_at, ?),
                deleted_at = COALESCE(deleted_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, now, lot_id),
        )
        return self.get_required(lot_id)

    def mark_purged(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        self.connection.execute(
            """
            UPDATE lots
            SET
                status = 'purge',
                title = NULL,
                idempotency_key = NULL,
                active_run_id = NULL,
                purge_requested_at = COALESCE(purge_requested_at, ?),
                bytes_uploaded = 0,
                bytes_artifacts = 0,
                artifacts_count = 0,
                problems_open_count = 0,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, lot_id),
        )
        return self.get_required(lot_id)

    def list_deleted_ready_for_purge(
        self,
        *,
        deleted_before: str | None = None,
    ) -> list[dict[str, Any]]:
        params: tuple[Any, ...]
        if deleted_before is None:
            where = "status = 'supprime'"
            params = ()
        else:
            where = "status = 'supprime' AND deleted_at IS NOT NULL AND deleted_at <= ?"
            params = (deleted_before,)
        rows = self.connection.execute(
            f"""
            SELECT * FROM lots
            WHERE {where}
            ORDER BY deleted_at ASC, id ASC
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def refresh_artifact_counters(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS artifacts_count, COALESCE(SUM(size_bytes), 0) AS size_bytes
            FROM artefacts
            WHERE lot_id = ? AND status = 'committed'
            """,
            (lot_id,),
        ).fetchone()
        self.connection.execute(
            """
            UPDATE lots
            SET artifacts_count = ?, bytes_artifacts = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                int(row["artifacts_count"]),
                int(row["size_bytes"]),
                now,
                lot_id,
            ),
        )
        return self.get_required(lot_id)

    def refresh_problem_counters(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS problems_open_count
            FROM problemes
            WHERE lot_id = ? AND status = 'open'
            """,
            (lot_id,),
        ).fetchone()
        self.connection.execute(
            """
            UPDATE lots
            SET problems_open_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (int(row["problems_open_count"]), now, lot_id),
        )
        return self.get_required(lot_id)
