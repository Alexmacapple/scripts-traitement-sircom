from __future__ import annotations

import shutil
from dataclasses import dataclass

from sircom2026.config import Settings
from sircom2026.database import Repositories
from sircom2026.state import record_problem
from sircom2026.worker import WorkerJobContext, WorkerLeaseLost


@dataclass(frozen=True)
class DiskFreeStatus:
    ok: bool
    code: str
    free_mb: int | None
    required_mb: int

    @property
    def details(self) -> dict[str, int]:
        details = {"required_mb": self.required_mb}
        if self.free_mb is not None:
            details["free_mb"] = self.free_mb
        return details


def check_disk_free(settings: Settings) -> DiskFreeStatus:
    try:
        usage = shutil.disk_usage(settings.data_dir)
    except OSError:
        return DiskFreeStatus(
            ok=False,
            code="SIRCOM_DISK_UNAVAILABLE",
            free_mb=None,
            required_mb=settings.disk_free_min_mb,
        )

    free_mb = usage.free // (1024 * 1024)
    if free_mb < settings.disk_free_min_mb:
        return DiskFreeStatus(
            ok=False,
            code="SIRCOM_DISK_FREE_LOW",
            free_mb=free_mb,
            required_mb=settings.disk_free_min_mb,
        )
    return DiskFreeStatus(
        ok=True,
        code="SIRCOM_DISK_OK",
        free_mb=free_mb,
        required_mb=settings.disk_free_min_mb,
    )


def record_disk_guard_problem(
    repositories: Repositories,
    *,
    context: WorkerJobContext,
    disk_status: DiskFreeStatus,
) -> None:
    if (
        repositories.jobs.get_committable_by_run(
            lot_id=context.lot_id,
            step_key=context.step_key,
            run_id=context.run_id,
            lease_version=context.leased_job.lease_version,
            expected_input_fingerprint=context.leased_job.input_fingerprint,
        )
        is None
    ):
        raise WorkerLeaseLost("Worker lease is no longer current.")

    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(context.step_key,),
    )
    problem = _disk_problem_definition(disk_status)
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=context.step_key,
        run_id=context.run_id,
        severity="bloquant",
        code=disk_status.code,
        title=problem["title"],
        cause=problem["cause"],
        action=problem["action"],
        technical=disk_status.details,
    )


def _disk_problem_definition(disk_status: DiskFreeStatus) -> dict[str, str]:
    if disk_status.code == "SIRCOM_DISK_UNAVAILABLE":
        return {
            "title": "Espace disque non vérifiable",
            "cause": "L'espace libre du répertoire de données Sircom n'a pas pu être vérifié.",
            "action": "Vérifier l'accès au répertoire de données, puis relancer l'étape.",
        }
    return {
        "title": "Espace disque insuffisant",
        "cause": "L'espace libre disponible pour les données Sircom est inférieur au seuil configuré.",
        "action": "Libérer de l'espace disque ou abaisser temporairement le seuil, puis relancer l'étape.",
    }
