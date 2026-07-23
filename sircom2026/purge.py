from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sircom2026.artifacts import safe_path_part
from sircom2026.config import Settings
from sircom2026.database import Database, Repositories
from sircom2026.lots import get_lot_detail


PURGE_TRACE_SCHEMA_VERSION = 1
PURGED_CHILD_TABLES = ("problemes", "evenements", "artefacts", "jobs", "etapes")


@dataclass(frozen=True)
class DirectoryUsage:
    bytes_count: int
    files_count: int


@dataclass(frozen=True)
class PurgeOutcome:
    lot: dict[str, Any]
    cancel_requested_jobs: int
    active_jobs_remaining: int
    purge_status: str
    trace: dict[str, Any] | None = None

    @property
    def deferred(self) -> bool:
        return self.active_jobs_remaining > 0


def delete_lot_and_purge_if_idle(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PurgeOutcome:
    existing_lot = repositories.lots.get_required(lot_id)
    if existing_lot["status"] == "purge":
        trace = repositories.purge_traces.get_by_lot_id_hash(lot_id_hash(lot_id))
        return PurgeOutcome(
            lot=get_lot_detail(repositories, lot_id),
            cancel_requested_jobs=0,
            active_jobs_remaining=0,
            purge_status="already_purged",
            trace=serialize_purge_trace(trace) if trace else None,
        )

    repositories.jobs.expire_stale_leases()
    active_jobs = repositories.jobs.count_active_for_lot(lot_id)
    cancel_requested_jobs = 0
    if active_jobs:
        cancel_requested_jobs = repositories.jobs.request_cancel_for_lot(lot_id)
        repositories.jobs.cancel_queued_for_lot(lot_id)

    if existing_lot["status"] != "supprime":
        lot = repositories.lots.mark_deleted(lot_id)
        repositories.events.create(
            lot_id=lot["id"],
            event_type="lot.deleted",
            payload={
                "lot_id": lot["id"],
                "active_jobs": active_jobs,
                "status": lot["status"],
            },
        )

    repositories.jobs.expire_stale_leases()
    active_jobs_remaining = repositories.jobs.count_processing_for_lot(lot_id)
    if active_jobs_remaining:
        return PurgeOutcome(
            lot=get_lot_detail(repositories, lot_id),
            cancel_requested_jobs=cancel_requested_jobs,
            active_jobs_remaining=active_jobs_remaining,
            purge_status="deferred",
        )

    outcome = purge_lot(repositories, settings=settings, lot_id=lot_id)
    return PurgeOutcome(
        lot=outcome.lot,
        cancel_requested_jobs=cancel_requested_jobs,
        active_jobs_remaining=0,
        purge_status=outcome.purge_status,
        trace=outcome.trace,
    )


def purge_lot(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PurgeOutcome:
    lot = repositories.lots.get_required(lot_id)
    repositories.jobs.expire_stale_leases()
    active_jobs_remaining = repositories.jobs.count_processing_for_lot(lot_id)
    if active_jobs_remaining:
        return PurgeOutcome(
            lot=get_lot_detail(repositories, lot_id),
            cancel_requested_jobs=0,
            active_jobs_remaining=active_jobs_remaining,
            purge_status="deferred",
        )
    if lot["status"] not in {"supprime", "purge"}:
        raise ValueError("Only deleted lots can be purged.")

    trace_hash = lot_id_hash(lot_id)
    lot_dir = lot_storage_dir(settings.data_dir, lot_id)
    existing_trace = repositories.purge_traces.get_by_lot_id_hash(trace_hash)
    if lot["status"] == "purge" and existing_trace and not lot_dir.exists():
        return PurgeOutcome(
            lot=get_lot_detail(repositories, lot_id),
            cancel_requested_jobs=0,
            active_jobs_remaining=0,
            purge_status="already_purged",
            trace=serialize_purge_trace(existing_trace),
        )

    if existing_trace and _trace_purge_status(existing_trace) == "started":
        trace_payload = json_dict(existing_trace["trace_json"])
        purged_at = existing_trace["purged_at"]
    else:
        trace_payload = build_purge_trace(repositories, lot=lot, lot_dir=lot_dir)
        purged_at = utc_now()
        trace_payload["purge"] = {
            "status": "started",
            "files_deleted": 0,
            "bytes_deleted": 0,
            "rows_deleted": {},
        }
        repositories.purge_traces.upsert(
            lot_id_hash=trace_hash,
            lot_created_at=lot["created_at"],
            lot_deleted_at=lot["deleted_at"],
            purged_at=purged_at,
            final_status=lot["status"],
            trace=trace_payload,
            trace_schema_version=PURGE_TRACE_SCHEMA_VERSION,
        )

    # The file deletion cannot roll back. Commit the recoverable "started" trace
    # and the deleted status before touching the filesystem.
    repositories.connection.commit()
    lot_dir_exists_before_delete = lot_dir.exists()
    deleted_usage = remove_lot_directory(lot_dir)
    if (
        existing_trace
        and not lot_dir_exists_before_delete
        and deleted_usage.files_count == 0
        and deleted_usage.bytes_count == 0
    ):
        deleted_usage = _usage_from_trace(trace_payload)
    rows_deleted: dict[str, int] = {}
    for table in PURGED_CHILD_TABLES:
        cursor = repositories.connection.execute(
            f"DELETE FROM {table} WHERE lot_id = ?",
            (lot_id,),
        )
        rows_deleted[table] = cursor.rowcount

    trace_payload["purge"] = {
        "status": "completed",
        "files_deleted": deleted_usage.files_count,
        "bytes_deleted": deleted_usage.bytes_count,
        "rows_deleted": rows_deleted,
    }
    trace_row = repositories.purge_traces.upsert(
        lot_id_hash=trace_hash,
        lot_created_at=lot["created_at"],
        lot_deleted_at=lot["deleted_at"],
        purged_at=purged_at,
        final_status="purge",
        trace=trace_payload,
        trace_schema_version=PURGE_TRACE_SCHEMA_VERSION,
    )
    purged_lot = repositories.lots.mark_purged(lot_id)
    return PurgeOutcome(
        lot=get_lot_detail(repositories, purged_lot["id"]),
        cancel_requested_jobs=0,
        active_jobs_remaining=0,
        purge_status="purged",
        trace=serialize_purge_trace(trace_row),
    )


def purge_expired_lots_for_settings(settings: Settings) -> list[PurgeOutcome]:
    database = Database(
        settings.sqlite_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    database.migrate()
    with database.transaction() as repositories:
        return purge_expired_lots(repositories, settings=settings)


def purge_deleted_lots_once(
    repositories: Repositories,
    *,
    settings: Settings,
    include_recent: bool = False,
) -> list[PurgeOutcome]:
    deleted_before = None
    if not include_recent:
        deleted_before = (
            datetime.now(UTC) - timedelta(days=settings.retention_days)
        ).isoformat(timespec="seconds")

    outcomes: list[PurgeOutcome] = []
    for lot in repositories.lots.list_deleted_ready_for_purge(
        deleted_before=deleted_before
    ):
        repositories.jobs.request_cancel_for_lot(lot["id"])
        repositories.jobs.cancel_queued_for_lot(lot["id"])
        repositories.jobs.expire_stale_leases()
        if repositories.jobs.count_processing_for_lot(lot["id"]):
            continue
        outcomes.append(purge_lot(repositories, settings=settings, lot_id=lot["id"]))
    prune_old_purge_traces(repositories, settings=settings)
    prune_old_quarantine_files(settings=settings)
    return outcomes


def purge_expired_lots(
    repositories: Repositories,
    *,
    settings: Settings,
) -> list[PurgeOutcome]:
    return purge_deleted_lots_once(
        repositories,
        settings=settings,
        include_recent=False,
    )


def prune_old_purge_traces(repositories: Repositories, *, settings: Settings) -> int:
    cutoff = (
        datetime.now(UTC) - timedelta(days=settings.purge_trace_retention_days)
    ).isoformat(timespec="seconds")
    return repositories.purge_traces.prune_before(cutoff)


def prune_old_quarantine_files(*, settings: Settings) -> int:
    quarantine_root = settings.data_dir / "quarantine"
    if not quarantine_root.exists():
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=settings.purge_trace_retention_days)
    removed_count = 0
    for path in quarantine_root.rglob("*"):
        if not path.is_file():
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if modified_at <= cutoff:
            path.unlink(missing_ok=True)
            removed_count += 1

    directories = sorted(
        (path for path in quarantine_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass
    return removed_count


def storage_summary(
    repositories: Repositories, *, settings: Settings
) -> dict[str, Any]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    data_usage = directory_usage(settings.data_dir)
    disk_usage = shutil.disk_usage(settings.data_dir)
    free_mb = disk_usage.free // (1024 * 1024)
    lot_items = storage_lot_items(repositories, settings=settings)
    active_lots = [item for item in lot_items if item["status"] != "purge"]
    latest_trace = repositories.purge_traces.latest()
    return {
        "data_dir": {
            "total_bytes": data_usage.bytes_count,
            "total_label": format_bytes(data_usage.bytes_count),
            "files_count": data_usage.files_count,
            "free_mb": free_mb,
            "required_free_mb": settings.disk_free_min_mb,
            "free_below_threshold": free_mb < settings.disk_free_min_mb,
        },
        "retention": {
            "days": settings.retention_days,
            "purge_interval_seconds": settings.purge_interval_seconds,
            "trace_retention_days": settings.purge_trace_retention_days,
        },
        "lots": active_lots,
        "biggest_lots": sorted(
            active_lots,
            key=lambda item: int(item["size_bytes"]),
            reverse=True,
        )[:5],
        "deleted_pending_purge_count": sum(
            1 for item in active_lots if item["status"] == "supprime"
        ),
        "purged_lots_count": sum(1 for item in lot_items if item["status"] == "purge"),
        "last_purge": serialize_purge_trace(latest_trace) if latest_trace else None,
    }


def storage_lot_items(
    repositories: Repositories,
    *,
    settings: Settings,
) -> list[dict[str, Any]]:
    rows = repositories.connection.execute(
        """
        SELECT id, status, created_at, deleted_at, bytes_uploaded, bytes_artifacts
        FROM lots
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        lot_dir = lot_storage_dir(settings.data_dir, row["id"])
        disk_usage = directory_usage(lot_dir)
        database_bytes = int(row["bytes_uploaded"] or 0) + int(
            row["bytes_artifacts"] or 0
        )
        size_bytes = max(disk_usage.bytes_count, database_bytes)
        items.append(
            {
                "id": row["id"],
                "status": row["status"],
                "created_at": row["created_at"],
                "deleted_at": row["deleted_at"],
                "size_bytes": size_bytes,
                "size_label": format_bytes(size_bytes),
                "files_count": disk_usage.files_count,
                "expires_at": lot_expiration(
                    row["deleted_at"], settings.retention_days
                ),
            }
        )
    return items


def build_purge_trace(
    repositories: Repositories,
    *,
    lot: dict[str, Any],
    lot_dir: Path,
) -> dict[str, Any]:
    artifacts = repositories.artifacts.list_all()
    lot_artifacts = [
        artifact for artifact in artifacts if artifact["lot_id"] == lot["id"]
    ]
    jobs = repositories.connection.execute(
        """
        SELECT status, error_code, started_at, finished_at
        FROM jobs
        WHERE lot_id = ?
        """,
        (lot["id"],),
    ).fetchall()
    steps = repositories.steps.list_for_lot(lot["id"])
    problems = repositories.problems.list_for_lot(
        lot["id"], include_resolved=True, limit=10000
    )
    events = repositories.events.list_for_lot(lot["id"], limit=10000)
    disk_usage = directory_usage(lot_dir)

    return {
        "schema_version": PURGE_TRACE_SCHEMA_VERSION,
        "lot": {
            "lot_id_hash": lot_id_hash(lot["id"]),
            "created_at": lot["created_at"],
            "deleted_at": lot["deleted_at"],
            "final_status_before_purge": lot["status"],
        },
        "durations": {
            "steps": step_durations(steps),
            "jobs": duration_stats(jobs),
        },
        "sizes": {
            "lot_dir_bytes": disk_usage.bytes_count,
            "artifact_bytes": sum(
                int(artifact["size_bytes"]) for artifact in lot_artifacts
            ),
        },
        "counters": {
            "files_count": disk_usage.files_count,
            "steps_by_status": counter_dict(step["status"] for step in steps),
            "jobs_by_status": counter_dict(job["status"] for job in jobs),
            "artifacts_by_status": counter_dict(
                artifact["status"] for artifact in lot_artifacts
            ),
            "artifacts_by_role": counter_dict(
                f"{artifact['kind']}:{artifact['role']}" for artifact in lot_artifacts
            ),
            "problems_by_code": counter_dict(problem["code"] for problem in problems),
            "problems_by_severity": counter_dict(
                problem["severity"] for problem in problems
            ),
            "events_by_type": counter_dict(event["event_type"] for event in events),
        },
        "technical_errors": sorted(
            {str(job["error_code"]) for job in jobs if job["error_code"]}
        ),
    }


def serialize_purge_trace(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "lot_id_hash": row["lot_id_hash"],
        "lot_created_at": row["lot_created_at"],
        "lot_deleted_at": row["lot_deleted_at"],
        "purged_at": row["purged_at"],
        "final_status": row["final_status"],
        "trace_schema_version": row["trace_schema_version"],
        "trace": json_dict(row["trace_json"]),
    }


def _trace_purge_status(row: dict[str, Any]) -> str | None:
    trace = json_dict(row["trace_json"])
    purge = trace.get("purge")
    if not isinstance(purge, dict):
        return None
    status = purge.get("status")
    return str(status) if status is not None else None


def _usage_from_trace(trace_payload: dict[str, Any]) -> DirectoryUsage:
    sizes = trace_payload.get("sizes")
    counters = trace_payload.get("counters")
    bytes_count = 0
    files_count = 0
    if isinstance(sizes, dict):
        bytes_count = int(sizes.get("lot_dir_bytes") or 0)
    if isinstance(counters, dict):
        files_count = int(counters.get("files_count") or 0)
    return DirectoryUsage(bytes_count=bytes_count, files_count=files_count)


def lot_storage_dir(data_dir: Path, lot_id: str) -> Path:
    return data_dir / "lots" / safe_path_part(lot_id, "lot_id")


def remove_lot_directory(lot_dir: Path) -> DirectoryUsage:
    usage = directory_usage(lot_dir)
    if lot_dir.exists():
        shutil.rmtree(lot_dir)
    return usage


def directory_usage(path: Path) -> DirectoryUsage:
    if not path.exists():
        return DirectoryUsage(bytes_count=0, files_count=0)
    if path.is_file():
        return DirectoryUsage(bytes_count=path.stat().st_size, files_count=1)

    bytes_count = 0
    files_count = 0
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        files_count += 1
        bytes_count += candidate.stat().st_size
    return DirectoryUsage(bytes_count=bytes_count, files_count=files_count)


def lot_id_hash(lot_id: str) -> str:
    return hashlib.sha256(f"sircom2026-purge-v1:{lot_id}".encode("utf-8")).hexdigest()


def lot_expiration(deleted_at: str | None, retention_days: int) -> str | None:
    if not deleted_at:
        return None
    deleted_at_datetime = parse_datetime(deleted_at)
    if deleted_at_datetime is None:
        return None
    return (deleted_at_datetime + timedelta(days=retention_days)).isoformat(
        timespec="seconds"
    )


def step_durations(steps: list[dict[str, Any]]) -> dict[str, int | None]:
    return {
        step["step_key"]: duration_ms(step["started_at"], step["finished_at"])
        for step in steps
        if step["started_at"] or step["finished_at"]
    }


def duration_stats(rows: list[Any]) -> dict[str, int]:
    durations = [
        value
        for value in (
            duration_ms(row["started_at"], row["finished_at"]) for row in rows
        )
        if value is not None
    ]
    return {
        "count": len(durations),
        "total_ms": sum(durations),
        "max_ms": max(durations, default=0),
    }


def duration_ms(started_at: str | None, finished_at: str | None) -> int | None:
    started = parse_datetime(started_at)
    finished = parse_datetime(finished_at)
    if started is None or finished is None or finished < started:
        return None
    return int((finished - started).total_seconds() * 1000)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def counter_dict(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value).items()))


def json_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} o"
    value = float(size_bytes)
    for unit in ("Ko", "Mo", "Go"):
        value /= 1024
        if value < 1024:
            return f"{value:.1f} {unit}"
    return f"{value / 1024:.1f} To"
