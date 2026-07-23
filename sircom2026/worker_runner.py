from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from typing import TextIO

from sircom2026.config import Settings, load_settings
from sircom2026.csv_contract import run_csv_contract_verification_job
from sircom2026.database import Database
from sircom2026.excel_diagnostic_pipeline import run_excel_diagnostic_job
from sircom2026.image_matching import run_image_matching_job
from sircom2026.images import run_image_inspection_job
from sircom2026.package import run_package_job
from sircom2026.purge import purge_deleted_lots_once
from sircom2026.reports import run_reports_job
from sircom2026.resource_guards import check_disk_free, record_disk_guard_problem
from sircom2026.transform import run_content_normalization_job, run_flat_merge_job
from sircom2026.worker import (
    JobHandler,
    JobResult,
    LocalWorker,
    WorkerJobContext,
    WorkerRunResult,
)


DISK_GUARDED_STEP_KEYS = frozenset({"matching_images", "package_final"})


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

    effective_handlers = (
        default_handlers(current_settings) if handlers is None else handlers
    )
    worker = LocalWorker(
        database,
        effective_handlers,
        worker_id=current_settings.worker_id,
        lease_seconds=current_settings.worker_lease_ttl_seconds,
        heartbeat_seconds=current_settings.worker_heartbeat_seconds,
        max_active_jobs=current_settings.max_active_jobs,
    )
    result = worker.run_once()
    with database.transaction() as repositories:
        purge_deleted_lots_once(
            repositories,
            settings=current_settings,
            include_recent=True,
        )
    return result


def default_handlers(settings: Settings) -> dict[str, JobHandler]:
    return _with_disk_guards(
        {
            "diagnostic_excel": lambda context: run_excel_diagnostic_job(
                context,
                settings=settings,
            ),
            "fusion_multi_onglets": lambda context: run_flat_merge_job(
                context,
                settings=settings,
            ),
            "normalisation_contenu": lambda context: run_content_normalization_job(
                context,
                settings=settings,
            ),
            "verification_csv_indesign": lambda context: run_csv_contract_verification_job(
                context,
                settings=settings,
            ),
            "inspection_images": lambda context: run_image_inspection_job(
                context,
                settings=settings,
            ),
            "matching_images": lambda context: run_image_matching_job(
                context,
                settings=settings,
            ),
            "rapports": lambda context: run_reports_job(
                context,
                settings=settings,
            ),
            "package_final": lambda context: run_package_job(
                context,
                settings=settings,
            ),
        },
        settings=settings,
    )


def _with_disk_guards(
    handlers: Mapping[str, JobHandler], *, settings: Settings
) -> dict[str, JobHandler]:
    guarded_handlers = dict(handlers)
    for step_key in DISK_GUARDED_STEP_KEYS:
        handler = guarded_handlers.get(step_key)
        if handler is not None:
            guarded_handlers[step_key] = _guard_disk_before_job(handler, settings)
    return guarded_handlers


def _guard_disk_before_job(handler: JobHandler, settings: Settings) -> JobHandler:
    def guarded(context: WorkerJobContext) -> JobResult:
        disk_status = check_disk_free(settings)
        if disk_status.ok:
            return handler(context)
        with context.database.transaction() as repositories:
            record_disk_guard_problem(
                repositories,
                context=context,
                disk_status=disk_status,
            )
        return JobResult(final_step_status="bloque")

    return guarded


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
