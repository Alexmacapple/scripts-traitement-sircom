from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from sircom2026._database_shared import (
    _fetch_one,
    _json,
    _new_id,
    _now,
)

__all__ = ["PurgeTracesRepository"]


class PurgeTracesRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert(
        self,
        *,
        lot_id_hash: str,
        lot_created_at: str | None,
        lot_deleted_at: str | None,
        purged_at: str,
        final_status: str,
        trace: Mapping[str, Any],
        trace_schema_version: int = 1,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_by_lot_id_hash(lot_id_hash)
        now = _now()
        if existing is None:
            row_id = trace_id or _new_id("purge_trace")
            self.connection.execute(
                """
                INSERT INTO purge_traces (
                    id, created_at, updated_at, lot_id_hash, lot_created_at,
                    lot_deleted_at, purged_at, final_status, trace_json,
                    trace_schema_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    now,
                    now,
                    lot_id_hash,
                    lot_created_at,
                    lot_deleted_at,
                    purged_at,
                    final_status,
                    _json(trace),
                    trace_schema_version,
                ),
            )
        else:
            row_id = existing["id"]
            self.connection.execute(
                """
                UPDATE purge_traces
                SET
                    updated_at = ?,
                    lot_created_at = ?,
                    lot_deleted_at = ?,
                    purged_at = ?,
                    final_status = ?,
                    trace_json = ?,
                    trace_schema_version = ?
                WHERE id = ?
                """,
                (
                    now,
                    lot_created_at,
                    lot_deleted_at,
                    purged_at,
                    final_status,
                    _json(trace),
                    trace_schema_version,
                    row_id,
                ),
            )
        return self.get_required(row_id)

    def get(self, trace_id: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM purge_traces WHERE id = ?",
            (trace_id,),
        )

    def get_required(self, trace_id: str) -> dict[str, Any]:
        row = self.get(trace_id)
        if row is None:
            raise KeyError(trace_id)
        return row

    def get_by_lot_id_hash(self, lot_id_hash: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM purge_traces WHERE lot_id_hash = ?",
            (lot_id_hash,),
        )

    def latest(self) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            """
            SELECT * FROM purge_traces
            ORDER BY purged_at DESC, id DESC
            LIMIT 1
            """,
            (),
        )

    def prune_before(self, cutoff: str) -> int:
        cursor = self.connection.execute(
            "DELETE FROM purge_traces WHERE purged_at < ?",
            (cutoff,),
        )
        return cursor.rowcount
