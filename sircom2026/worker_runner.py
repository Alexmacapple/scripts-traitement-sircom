from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from typing import TextIO

from sircom2026.config import Settings, load_settings
from sircom2026.database import Database
from sircom2026.excel_diagnostic_pipeline import run_excel_diagnostic_job
from sircom2026.transform import run_flat_merge_job
from sircom2026.worker import JobHandler, LocalWorker, WorkerRunResult


def run_worker_once(
    *,
    settings: Settings | None = None,
    handlers: Mapping[str, JobHandler] | None = None,
) -> WorkerRunResult:
    current_settings = settings or load_settings()
    if not current_settings.worker_enabled:
        return WorkerRunResult(processed=False, outcome="disabled")

    database = Database(
        current_settings.sqlite_path,
        busy_timeout_ms=current_settings.sqlite_busy_timeout_ms,
    )
    database.migrate()
    with database.transaction() as repositories:
        repositories.jobs.expire_stale_leases()

    effective_handlers = default_handlers(current_settings) if handlers is None else handlers
    worker = LocalWorker(
        database,
        effective_handlers,
        worker_id=current_settings.worker_id,
        lease_seconds=current_settings.worker_lease_ttl_seconds,
        max_active_jobs=current_settings.max_active_jobs,
    )
    return worker.run_once()


def default_handlers(settings: Settings) -> dict[str, JobHandler]:
    return {
        "diagnostic_excel": lambda context: run_excel_diagnostic_job(
            context,
            settings=settings,
        ),
        "fusion_multi_onglets": lambda context: run_flat_merge_job(
            context,
            settings=settings,
        ),
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    handlers: Mapping[str, JobHandler] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Run one Sircom 2026 local worker acquisition.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one acquisition cycle. This is currently the only mode.",
    )
    parser.parse_args(argv)

    result = run_worker_once(handlers=handlers)
    output = stdout or sys.stdout
    print(
        "processed={processed} outcome={outcome} job_id={job_id} step_key={step_key}".format(
            processed=str(result.processed).lower(),
            outcome=result.outcome,
            job_id=result.job_id or "",
            step_key=result.step_key or "",
        ),
        file=output,
    )
    return 0 if result.outcome in {"disabled", "idle", "succeeded", "canceled"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
