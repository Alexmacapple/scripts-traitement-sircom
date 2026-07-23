from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from sircom2026._database_lots import LotsRepository
from sircom2026._database_shared import (
    ARTIFACT_STATUSES,
    _fetch_one,
    _json,
    _new_id,
    _now,
    _placeholders,
    _validate_choice,
)

__all__ = ["ArtifactsRepository"]


class ArtifactsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        kind: str,
        role: str,
        relative_path: str,
        sha256: str,
        size_bytes: int,
        mime_type: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        status: str = "pending",
        artifact_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("artifact status", status, ARTIFACT_STATUSES)
        now = _now()
        row_id = artifact_id or _new_id("artifact")
        self.connection.execute(
            """
            INSERT INTO artefacts (
                id, created_at, updated_at, lot_id, step_key, run_id, status,
                kind, role, relative_path, sha256, size_bytes, schema_version,
                mime_type, metadata_json
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
                status,
                kind,
                role,
                relative_path,
                sha256,
                size_bytes,
                1,
                mime_type,
                _json(metadata or {}),
            ),
        )
        return self.get_required(row_id)

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection, "SELECT * FROM artefacts WHERE id = ?", (artifact_id,)
        )

    def get_required(self, artifact_id: str) -> dict[str, Any]:
        row = self.get(artifact_id)
        if row is None:
            raise KeyError(artifact_id)
        return row

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM artefacts ORDER BY created_at, id"
        ).fetchall()
        return [dict(row) for row in rows]

    def get_for_lot(self, lot_id: str, artifact_id: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM artefacts WHERE lot_id = ? AND id = ?",
            (lot_id, artifact_id),
        )

    def get_for_step_run_role(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        role: str,
    ) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            """
            SELECT * FROM artefacts
            WHERE lot_id = ?
              AND step_key = ?
              AND run_id = ?
              AND role = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (lot_id, step_key, run_id, role),
        )

    def update_status(self, artifact_id: str, status: str) -> dict[str, Any]:
        _validate_choice("artifact status", status, ARTIFACT_STATUSES)
        now = _now()
        timestamp_column = {
            "committed": "committed_at",
            "obsolete": "obsoleted_at",
            "deleted": "deleted_at",
            "quarantined": "quarantined_at",
        }.get(status)
        if timestamp_column is None:
            self.connection.execute(
                "UPDATE artefacts SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, artifact_id),
            )
        else:
            self.connection.execute(
                f"""
                UPDATE artefacts
                SET status = ?, {timestamp_column} = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, now, now, artifact_id),
            )
        return self.get_required(artifact_id)

    def mark_obsolete_for_steps(
        self, *, lot_id: str, step_keys: tuple[str, ...]
    ) -> int:
        if not step_keys:
            return 0
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE artefacts
            SET
                status = 'obsolete',
                obsoleted_at = COALESCE(obsoleted_at, ?),
                updated_at = ?
            WHERE lot_id = ?
              AND step_key IN ({_placeholders(len(step_keys))})
              AND status IN ('pending', 'committed')
            """,
            (now, now, lot_id, *step_keys),
        )
        LotsRepository(self.connection).refresh_artifact_counters(lot_id)
        return cursor.rowcount
