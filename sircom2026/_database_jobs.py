from __future__ import annotations

import sqlite3
from typing import Any

from sircom2026._database_lots import LotsRepository
from sircom2026._database_shared import (
    ACTIVE_JOB_STATUSES,
    COMMITTABLE_JOB_STATUSES,
    JOB_STATUSES,
    LOT_WRITE_BLOCKED_STATUSES,
    _check_in,
    _fetch_one,
    _new_id,
    _now,
    _now_plus,
    _placeholders,
    _validate_choice,
)

__all__ = ["JobsRepository"]


class JobsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        idempotency_key: str,
        status: str = "queued",
        job_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("job status", status, JOB_STATUSES)
        lot = LotsRepository(self.connection).get_required(lot_id)
        if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot create a job for a canceled or deleted lot.")
        now = _now()
        row_id = job_id or _new_id("job")
        self.connection.execute(
            """
            INSERT INTO jobs (
                id, created_at, updated_at, lot_id, step_key, status, run_id,
                idempotency_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, now, now, lot_id, step_key, status, run_id, idempotency_key),
        )
        return self.get_required(row_id)

    def create_owned_running(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        idempotency_key: str,
        lease_owner: str,
        lease_seconds: int,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than 0.")
        job = self.create(
            lot_id=lot_id,
            step_key=step_key,
            run_id=run_id,
            idempotency_key=idempotency_key,
            status="running",
            job_id=job_id,
        )
        now = _now()
        self.connection.execute(
            """
            UPDATE jobs
            SET
                lease_owner = ?,
                lease_version = 1,
                lease_until = ?,
                heartbeat_at = ?,
                started_at = COALESCE(started_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (
                lease_owner,
                _now_plus(seconds=lease_seconds),
                now,
                now,
                now,
                job["id"],
            ),
        )
        return self.get_required(job["id"])

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM jobs WHERE id = ?", (job_id,))

    def get_required(self, job_id: str) -> dict[str, Any]:
        row = self.get(job_id)
        if row is None:
            raise KeyError(job_id)
        return row

    def get_by_idempotency_key(
        self,
        *,
        lot_id: str,
        step_key: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            """
            SELECT * FROM jobs
            WHERE lot_id = ? AND step_key = ? AND idempotency_key = ?
            """,
            (lot_id, step_key, idempotency_key),
        )

    def get_active_for_step(
        self, *, lot_id: str, step_key: str
    ) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            f"""
            SELECT * FROM jobs
            WHERE jobs.lot_id = ?
              AND step_key = ?
              AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (lot_id, step_key),
        )

    def get_committable_by_run(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        lease_version: int,
        expected_input_fingerprint: str | None = None,
    ) -> dict[str, Any] | None:
        params: list[Any] = [lot_id, step_key, run_id, _now()]
        params.append(lease_version)
        params.extend([expected_input_fingerprint, expected_input_fingerprint])
        return _fetch_one(
            self.connection,
            f"""
            SELECT jobs.* FROM jobs
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            WHERE jobs.lot_id = ?
              AND jobs.step_key = ?
              AND jobs.run_id = ?
              AND jobs.status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND jobs.lease_until IS NOT NULL
              AND jobs.lease_until > ?
              AND etapes.current_run_id = jobs.run_id
              AND jobs.lease_version = ?
              AND (? IS NULL OR etapes.input_fingerprint = ?)
            ORDER BY jobs.created_at DESC
            LIMIT 1
            """,
            tuple(params),
        )

    def get_owned_committable(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        expected_input_fingerprint: str | None = None,
        allow_blocked_lot: bool = False,
    ) -> dict[str, Any] | None:
        lot_filter = (
            ""
            if allow_blocked_lot
            else f"AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})"
        )
        return _fetch_one(
            self.connection,
            f"""
            SELECT jobs.* FROM jobs
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            JOIN lots
              ON lots.id = jobs.lot_id
            WHERE jobs.id = ?
              AND jobs.lease_owner = ?
              AND jobs.run_id = ?
              AND jobs.lease_version = ?
              AND jobs.status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND jobs.lease_until IS NOT NULL
              AND jobs.lease_until > ?
              AND etapes.current_run_id = jobs.run_id
              AND (? IS NULL OR etapes.input_fingerprint = ?)
              {lot_filter}
            LIMIT 1
            """,
            (
                job_id,
                worker_id,
                run_id,
                lease_version,
                _now(),
                expected_input_fingerprint,
                expected_input_fingerprint,
            ),
        )

    def update_status(self, job_id: str, status: str) -> dict[str, Any]:
        _validate_choice("job status", status, JOB_STATUSES)
        now = _now()
        is_started = 1 if status in {"leased", "running"} else 0
        is_finished = 1 if status in {"succeeded", "failed", "canceled"} else 0
        self.connection.execute(
            """
            UPDATE jobs
            SET
                status = ?,
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
            (status, now, is_started, now, is_finished, now, job_id),
        )
        return self.get_required(job_id)

    def acquire_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
        max_active_jobs: int = 1,
        step_keys: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than 0.")
        if max_active_jobs <= 0:
            raise ValueError("max_active_jobs must be greater than 0.")
        if step_keys is not None and not step_keys:
            return None

        self.expire_stale_leases()
        if self.count_processing() >= max_active_jobs:
            return None
        now = _now()
        lease_until = _now_plus(seconds=lease_seconds)
        step_filter = ""
        priority_order = "jobs.created_at ASC, jobs.id ASC"
        params: list[Any] = [now]
        if step_keys is not None:
            step_filter = f"AND jobs.step_key IN ({_placeholders(len(step_keys))})"
            params.extend(step_keys)
            priority_cases = " ".join(
                f"WHEN ? THEN {index}" for index, _step_key in enumerate(step_keys)
            )
            priority_order = (
                "jobs.created_at ASC, "
                f"CASE jobs.step_key {priority_cases} ELSE {len(step_keys)} END ASC, "
                "jobs.id ASC"
            )
            params.extend(step_keys)
        row = self.connection.execute(
            f"""
            SELECT jobs.id
            FROM jobs
            JOIN lots
              ON lots.id = jobs.lot_id
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            WHERE (
                  jobs.status = 'queued'
                  OR (
                      jobs.status = 'expired'
                      AND jobs.lease_until IS NOT NULL
                      AND jobs.lease_until <= ?
                  )
              )
              AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
              AND etapes.status NOT IN ('annule', 'termine', 'termine_avec_alertes', 'bloque')
              AND etapes.current_run_id = jobs.run_id
              {step_filter}
            ORDER BY {priority_order}
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
        if row is None:
            return None

        cursor = self.connection.execute(
            """
            UPDATE jobs
            SET
                status = 'leased',
                lease_owner = ?,
                lease_version = lease_version + 1,
                lease_until = ?,
                heartbeat_at = ?,
                started_at = COALESCE(started_at, ?),
                attempt = attempt + 1,
                updated_at = ?
            WHERE id = ?
              AND status IN ('queued', 'expired')
            """,
            (worker_id, lease_until, now, now, now, row["id"]),
        )
        if cursor.rowcount != 1:
            return None
        return self._get_with_step_input(row["id"])

    def count_processing(self) -> int:
        row = self.connection.execute(
            f"""
            SELECT COUNT(*) FROM jobs
            JOIN lots
              ON lots.id = jobs.lot_id
            WHERE jobs.status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
            """
        ).fetchone()
        return int(row[0])

    def mark_running(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
    ) -> dict[str, Any] | None:
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET
                status = 'running',
                started_at = COALESCE(started_at, ?),
                heartbeat_at = ?,
                updated_at = ?
            WHERE id = ?
              AND lease_owner = ?
              AND run_id = ?
              AND lease_version = ?
              AND status = 'leased'
              AND lease_until IS NOT NULL
              AND lease_until > ?
              AND EXISTS (
                  SELECT 1 FROM etapes
                  JOIN lots
                    ON lots.id = etapes.lot_id
                  WHERE etapes.lot_id = jobs.lot_id
                    AND etapes.step_key = jobs.step_key
                    AND etapes.current_run_id = jobs.run_id
                    AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
              )
            """,
            (now, now, now, job_id, worker_id, run_id, lease_version, now),
        )
        if cursor.rowcount != 1:
            return None
        return self.get_required(job_id)

    def heartbeat(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        lease_seconds: int,
    ) -> dict[str, Any] | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than 0.")
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET lease_until = ?, heartbeat_at = ?, updated_at = ?
            WHERE id = ?
              AND lease_owner = ?
              AND run_id = ?
              AND lease_version = ?
              AND status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND lease_until IS NOT NULL
              AND lease_until > ?
              AND EXISTS (
                  SELECT 1
                  FROM etapes
                  JOIN lots
                    ON lots.id = etapes.lot_id
                  WHERE etapes.lot_id = jobs.lot_id
                    AND etapes.step_key = jobs.step_key
                    AND etapes.current_run_id = jobs.run_id
                    AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
              )
            """,
            (
                _now_plus(seconds=lease_seconds),
                now,
                now,
                job_id,
                worker_id,
                run_id,
                lease_version,
                now,
            ),
        )
        if cursor.rowcount != 1:
            return None
        return self.get_required(job_id)

    def update_progress(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        current: int,
        total: int,
        lease_seconds: int,
    ) -> dict[str, Any] | None:
        if current < 0 or total < 0 or current > total:
            raise ValueError("progress must satisfy 0 <= current <= total.")
        job = self.heartbeat(
            job_id=job_id,
            worker_id=worker_id,
            run_id=run_id,
            lease_version=lease_version,
            lease_seconds=lease_seconds,
        )
        if job is None:
            return None
        self.connection.execute(
            """
            UPDATE etapes
            SET progress_current = ?, progress_total = ?, updated_at = ?
            WHERE lot_id = ? AND step_key = ?
            """,
            (current, total, _now(), job["lot_id"], job["step_key"]),
        )
        return self.get_required(job_id)

    def finish_owned(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        expected_input_fingerprint: str | None = None,
        allow_blocked_lot: bool = False,
    ) -> dict[str, Any] | None:
        if status not in {"succeeded", "failed", "canceled"}:
            raise ValueError(
                "Owned job can only finish as succeeded, failed or canceled."
            )
        if (
            self.get_owned_committable(
                job_id=job_id,
                worker_id=worker_id,
                run_id=run_id,
                lease_version=lease_version,
                expected_input_fingerprint=expected_input_fingerprint,
                allow_blocked_lot=allow_blocked_lot,
            )
            is None
        ):
            return None
        now = _now()
        self.connection.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                finished_at = COALESCE(finished_at, ?),
                heartbeat_at = ?,
                error_code = ?,
                error_message = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (status, now, now, error_code, error_message, now, job_id),
        )
        return self.get_required(job_id)

    def _get_with_step_input(self, job_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT jobs.*, etapes.input_fingerprint AS step_input_fingerprint
            FROM jobs
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            WHERE jobs.id = ?
            """,
            (job_id,),
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return dict(row)

    def expire_stale_leases(self) -> int:
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET status = 'expired', updated_at = ?
            WHERE status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND lease_until IS NOT NULL
              AND lease_until <= ?
            """,
            (_now(), _now()),
        )
        return cursor.rowcount

    def count_active_for_lot(self, lot_id: str) -> int:
        row = self.connection.execute(
            f"""
            SELECT COUNT(*) FROM jobs
            WHERE lot_id = ? AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            """,
            (lot_id,),
        ).fetchone()
        return int(row[0])

    def count_processing_for_lot(self, lot_id: str) -> int:
        row = self.connection.execute(
            f"""
            SELECT COUNT(*) FROM jobs
            WHERE lot_id = ? AND status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
            """,
            (lot_id,),
        ).fetchone()
        return int(row[0])

    def request_cancel_for_lot(self, lot_id: str) -> int:
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET cancel_requested_at = COALESCE(cancel_requested_at, ?), updated_at = ?
            WHERE lot_id = ? AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            """,
            (now, now, lot_id),
        )
        return cursor.rowcount

    def cancel_queued_for_lot(self, lot_id: str) -> int:
        now = _now()
        cursor = self.connection.execute(
            """
            UPDATE jobs
            SET
                status = 'canceled',
                cancel_requested_at = COALESCE(cancel_requested_at, ?),
                finished_at = COALESCE(finished_at, ?),
                updated_at = ?
            WHERE lot_id = ? AND status = 'queued'
            """,
            (now, now, now, lot_id),
        )
        return cursor.rowcount

    def cancel_active_for_step(self, lot_id: str, step_key: str) -> int:
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET
                status = 'canceled',
                cancel_requested_at = COALESCE(cancel_requested_at, ?),
                finished_at = COALESCE(finished_at, ?),
                updated_at = ?
            WHERE lot_id = ?
              AND step_key = ?
              AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            """,
            (now, now, now, lot_id, step_key),
        )
        return cursor.rowcount
