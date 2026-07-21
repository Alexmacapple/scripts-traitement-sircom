from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sircom2026.database import Database, Repositories
from sircom2026.pipeline import FINGERPRINT_REQUIRED_STEP_KEYS
from sircom2026.state import complete_step, require_human_validation, transition_step


class WorkerCancelled(RuntimeError):
    """Raised inside a handler when a cooperative cancellation is observed."""


class WorkerLeaseLost(RuntimeError):
    """Raised when the current worker no longer owns the job lease."""


@dataclass(frozen=True)
class JobResult:
    with_warnings: bool = False
    output_fingerprint: str | None = None
    expected_input_fingerprint: str | None = None
    final_step_status: str | None = None
    enqueue_next_steps: tuple[str, ...] = ()
    require_next_validations: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnqueuedJob:
    job: dict[str, Any]
    created: bool


@dataclass(frozen=True)
class LeasedJob:
    job_id: str
    lot_id: str
    step_key: str
    run_id: str
    lease_version: int
    input_fingerprint: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> LeasedJob:
        return cls(
            job_id=str(row["id"]),
            lot_id=str(row["lot_id"]),
            step_key=str(row["step_key"]),
            run_id=str(row["run_id"]),
            lease_version=int(row["lease_version"]),
            input_fingerprint=row.get("step_input_fingerprint"),
        )


@dataclass(frozen=True)
class WorkerRunResult:
    processed: bool
    outcome: str
    job_id: str | None = None
    step_key: str | None = None


@dataclass(frozen=True)
class WorkerJobContext:
    database: Database
    leased_job: LeasedJob
    worker_id: str
    lease_seconds: int

    @property
    def lot_id(self) -> str:
        return self.leased_job.lot_id

    @property
    def step_key(self) -> str:
        return self.leased_job.step_key

    @property
    def run_id(self) -> str:
        return self.leased_job.run_id

    def heartbeat(self) -> None:
        with self.database.transaction() as repositories:
            job = repositories.jobs.heartbeat(
                job_id=self.leased_job.job_id,
                worker_id=self.worker_id,
                run_id=self.leased_job.run_id,
                lease_version=self.leased_job.lease_version,
                lease_seconds=self.lease_seconds,
            )
            if job is None:
                raise WorkerLeaseLost("Worker lease is no longer current.")
            _raise_if_cancel_requested(repositories, job)

    def set_progress(self, current: int, total: int) -> None:
        with self.database.transaction() as repositories:
            job = repositories.jobs.update_progress(
                job_id=self.leased_job.job_id,
                worker_id=self.worker_id,
                run_id=self.leased_job.run_id,
                lease_version=self.leased_job.lease_version,
                current=current,
                total=total,
                lease_seconds=self.lease_seconds,
            )
            if job is None:
                raise WorkerLeaseLost("Worker lease is no longer current.")
            repositories.events.create(
                lot_id=job["lot_id"],
                step_key=job["step_key"],
                run_id=job["run_id"],
                event_type="job.progress",
                payload={
                    "job_id": job["id"],
                    "progress_current": current,
                    "progress_total": total,
                    "run_id": job["run_id"],
                    "step_key": job["step_key"],
                },
            )
            _raise_if_cancel_requested(repositories, job)

    def raise_if_cancelled(self) -> None:
        with self.database.session() as repositories:
            job = repositories.jobs.get_required(self.leased_job.job_id)
            _raise_if_cancel_requested(repositories, job)


JobHandler = Callable[[WorkerJobContext], JobResult]


class LocalWorker:
    def __init__(
        self,
        database: Database,
        handlers: Mapping[str, JobHandler],
        *,
        worker_id: str = "local-1",
        lease_seconds: int = 300,
        max_active_jobs: int = 1,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than 0.")
        if max_active_jobs <= 0:
            raise ValueError("max_active_jobs must be greater than 0.")
        self.database = database
        self.handlers = dict(handlers)
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.max_active_jobs = max_active_jobs

    def acquire_next(self) -> LeasedJob | None:
        step_keys = tuple(self.handlers)
        if not step_keys:
            return None
        with self.database.transaction() as repositories:
            job = repositories.jobs.acquire_next(
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
                max_active_jobs=self.max_active_jobs,
                step_keys=step_keys,
            )
            if job is None:
                return None
            repositories.events.create(
                lot_id=job["lot_id"],
                step_key=job["step_key"],
                run_id=job["run_id"],
                event_type="job.acquired",
                payload={
                    "attempt": job["attempt"],
                    "job_id": job["id"],
                    "lease_version": job["lease_version"],
                    "run_id": job["run_id"],
                    "step_key": job["step_key"],
                    "worker_id": self.worker_id,
                },
            )
            return LeasedJob.from_row(job)

    def start_job(self, leased_job: LeasedJob) -> bool:
        with self.database.transaction() as repositories:
            job = repositories.jobs.mark_running(
                job_id=leased_job.job_id,
                worker_id=self.worker_id,
                run_id=leased_job.run_id,
                lease_version=leased_job.lease_version,
            )
            if job is None:
                _record_finish_rejected(
                    repositories,
                    leased_job=leased_job,
                    reason="lease_not_current",
                )
                return False
            transition_step(
                repositories,
                lot_id=job["lot_id"],
                step_key=job["step_key"],
                status="en_cours",
                run_id=job["run_id"],
                event_type="job.started",
            )
            return True

    def finish_success(self, leased_job: LeasedJob, result: JobResult | None = None) -> bool:
        job_result = result or JobResult()
        expected_input_fingerprint = (
            job_result.expected_input_fingerprint
            if job_result.expected_input_fingerprint is not None
            else leased_job.input_fingerprint
        )
        if (
            leased_job.step_key in FINGERPRINT_REQUIRED_STEP_KEYS
            and expected_input_fingerprint is None
        ):
            self.record_rejected_finish(
                leased_job,
                reason="input_fingerprint_missing",
            )
            return False
        with self.database.transaction() as repositories:
            job = repositories.jobs.finish_owned(
                job_id=leased_job.job_id,
                worker_id=self.worker_id,
                run_id=leased_job.run_id,
                lease_version=leased_job.lease_version,
                status="succeeded",
                expected_input_fingerprint=expected_input_fingerprint,
            )
            if job is None:
                _record_finish_rejected(
                    repositories,
                    leased_job=leased_job,
                    reason="lease_or_run_not_current",
                )
                return False
            if job_result.output_fingerprint is not None:
                repositories.steps.set_output_fingerprint(
                    lot_id=job["lot_id"],
                    step_key=job["step_key"],
                    output_fingerprint=job_result.output_fingerprint,
                    run_id=job["run_id"],
                )
            if job_result.final_step_status == "bloque":
                transition_step(
                    repositories,
                    lot_id=job["lot_id"],
                    step_key=job["step_key"],
                    status="bloque",
                    run_id=job["run_id"],
                    event_type="step.blocked",
                )
            else:
                complete_step(
                    repositories,
                    lot_id=job["lot_id"],
                    step_key=job["step_key"],
                    run_id=job["run_id"],
                    with_warnings=job_result.with_warnings,
                )
                if job_result.enqueue_next_steps:
                    from sircom2026.invalidation import step_input_fingerprint

                    for next_step_key in job_result.enqueue_next_steps:
                        next_input_fingerprint = step_input_fingerprint(
                            repositories,
                            lot_id=job["lot_id"],
                            step_key=next_step_key,
                        )
                        enqueue_job(
                            repositories,
                            lot_id=job["lot_id"],
                            step_key=next_step_key,
                            idempotency_key=(
                                f"{next_step_key}:{job['step_key']}:{job['run_id']}"
                            ),
                            input_fingerprint=next_input_fingerprint,
                        )
                if job_result.require_next_validations:
                    from sircom2026.invalidation import step_input_fingerprint

                    for next_step_key in job_result.require_next_validations:
                        next_input_fingerprint = step_input_fingerprint(
                            repositories,
                            lot_id=job["lot_id"],
                            step_key=next_step_key,
                        )
                        next_run_id = _new_run_id()
                        repositories.steps.prepare_run(
                            lot_id=job["lot_id"],
                            step_key=next_step_key,
                            run_id=next_run_id,
                            input_fingerprint=next_input_fingerprint,
                        )
                        require_human_validation(
                            repositories,
                            lot_id=job["lot_id"],
                            step_key=next_step_key,
                            run_id=next_run_id,
                        )
            repositories.events.create(
                lot_id=job["lot_id"],
                step_key=job["step_key"],
                run_id=job["run_id"],
                event_type="job.succeeded",
                payload={
                    "job_id": job["id"],
                    "run_id": job["run_id"],
                    "status": job["status"],
                    "step_key": job["step_key"],
                },
            )
            return True

    def finish_canceled(self, leased_job: LeasedJob) -> bool:
        with self.database.transaction() as repositories:
            job = repositories.jobs.finish_owned(
                job_id=leased_job.job_id,
                worker_id=self.worker_id,
                run_id=leased_job.run_id,
                lease_version=leased_job.lease_version,
                status="canceled",
            )
            if job is None:
                _record_finish_rejected(
                    repositories,
                    leased_job=leased_job,
                    reason="lease_or_run_not_current",
                )
                return False
            step = repositories.steps.get_by_lot_key(job["lot_id"], job["step_key"])
            if step is None:
                raise KeyError(f"{job['lot_id']}:{job['step_key']}")
            repositories.steps.update_status(step["id"], "annule", run_id=job["run_id"])
            repositories.lots.update_status(job["lot_id"], "annule")
            repositories.events.create(
                lot_id=job["lot_id"],
                step_key=job["step_key"],
                run_id=job["run_id"],
                level="warning",
                event_type="job.canceled",
                payload={
                    "job_id": job["id"],
                    "run_id": job["run_id"],
                    "status": job["status"],
                    "step_key": job["step_key"],
                },
            )
            return True

    def finish_failed(self, leased_job: LeasedJob, exc: BaseException) -> bool:
        error_code = exc.__class__.__name__
        with self.database.transaction() as repositories:
            job = repositories.jobs.finish_owned(
                job_id=leased_job.job_id,
                worker_id=self.worker_id,
                run_id=leased_job.run_id,
                lease_version=leased_job.lease_version,
                status="failed",
                error_code=error_code,
                error_message=error_code,
            )
            if job is None:
                _record_finish_rejected(
                    repositories,
                    leased_job=leased_job,
                    reason="lease_or_run_not_current",
                )
                return False
            from sircom2026.state import fail_step

            fail_step(
                repositories,
                lot_id=job["lot_id"],
                step_key=job["step_key"],
                run_id=job["run_id"],
                code="SIRCOM_WORKER_UNEXPECTED_ERROR",
                title="Erreur technique du worker",
                cause="Le traitement local s'est interrompu sur une erreur inattendue.",
                action="Consulter le journal technique, corriger la cause puis relancer l'etape.",
                technical={"error_code": error_code},
            )
            return True

    def run_once(self) -> WorkerRunResult:
        leased_job = self.acquire_next()
        if leased_job is None:
            return WorkerRunResult(processed=False, outcome="idle")
        if not self.start_job(leased_job):
            return WorkerRunResult(
                processed=True,
                outcome="rejected",
                job_id=leased_job.job_id,
                step_key=leased_job.step_key,
            )

        context = WorkerJobContext(
            database=self.database,
            leased_job=leased_job,
            worker_id=self.worker_id,
            lease_seconds=self.lease_seconds,
        )
        handler = self.handlers[leased_job.step_key]
        try:
            context.raise_if_cancelled()
            result = handler(context)
            context.raise_if_cancelled()
        except WorkerCancelled:
            outcome = "canceled" if self.finish_canceled(leased_job) else "rejected"
        except WorkerLeaseLost:
            self.record_rejected_finish(leased_job, reason="lease_lost")
            outcome = "rejected"
        except Exception as exc:
            outcome = "failed" if self.finish_failed(leased_job, exc) else "rejected"
        else:
            outcome = "succeeded" if self.finish_success(leased_job, result) else "rejected"

        return WorkerRunResult(
            processed=True,
            outcome=outcome,
            job_id=leased_job.job_id,
            step_key=leased_job.step_key,
        )

    def record_rejected_finish(self, leased_job: LeasedJob, *, reason: str) -> None:
        with self.database.transaction() as repositories:
            _record_finish_rejected(
                repositories,
                leased_job=leased_job,
                reason=reason,
            )


def enqueue_job(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    idempotency_key: str,
    run_id: str | None = None,
    input_fingerprint: str | None = None,
) -> EnqueuedJob:
    existing = repositories.jobs.get_by_idempotency_key(
        lot_id=lot_id,
        step_key=step_key,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return EnqueuedJob(existing, created=False)

    active_job = repositories.jobs.get_active_for_step(lot_id=lot_id, step_key=step_key)
    if active_job is not None:
        return EnqueuedJob(active_job, created=False)

    next_run_id = run_id or _new_run_id()
    repositories.steps.prepare_run(
        lot_id=lot_id,
        step_key=step_key,
        run_id=next_run_id,
        input_fingerprint=input_fingerprint,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=next_run_id,
        event_type="step.ready",
        payload={
            "input_fingerprint": input_fingerprint,
            "run_id": next_run_id,
            "status": "pret",
            "step_key": step_key,
        },
    )
    job = repositories.jobs.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=next_run_id,
        idempotency_key=idempotency_key,
        status="queued",
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=next_run_id,
        event_type="job.queued",
        payload={
            "job_id": job["id"],
            "run_id": next_run_id,
            "status": job["status"],
            "step_key": step_key,
        },
    )
    from sircom2026.state import recompute_lot_status

    recompute_lot_status(repositories, lot_id)
    return EnqueuedJob(job, created=True)


def request_lot_cancellation(repositories: Repositories, lot_id: str) -> tuple[dict[str, Any], int]:
    lot = repositories.lots.request_cancel(lot_id)
    active_jobs = repositories.jobs.request_cancel_for_lot(lot_id)
    repositories.events.create(
        lot_id=lot_id,
        level="warning",
        event_type="lot.cancel_requested",
        payload={
            "active_jobs": active_jobs,
            "lot_id": lot_id,
            "status": lot["status"],
        },
    )
    return lot, active_jobs


def _raise_if_cancel_requested(repositories: Repositories, job: Mapping[str, Any]) -> None:
    lot = repositories.lots.get_required(str(job["lot_id"]))
    if job["cancel_requested_at"] or lot["cancel_requested_at"] or lot["delete_requested_at"]:
        raise WorkerCancelled("Cancellation requested.")


def _record_finish_rejected(
    repositories: Repositories,
    *,
    leased_job: LeasedJob,
    reason: str,
) -> None:
    repositories.events.create(
        lot_id=leased_job.lot_id,
        step_key=leased_job.step_key,
        run_id=leased_job.run_id,
        level="warning",
        event_type="job.finish_rejected",
        payload={
            "job_id": leased_job.job_id,
            "lease_version": leased_job.lease_version,
            "reason": reason,
            "run_id": leased_job.run_id,
            "step_key": leased_job.step_key,
        },
    )


def _new_run_id() -> str:
    return f"run_{uuid.uuid4().hex}"
