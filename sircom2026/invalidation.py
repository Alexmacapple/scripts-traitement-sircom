from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sircom2026.database import (
    ACTIVE_JOB_STATUSES,
    LOT_WRITE_BLOCKED_STATUSES,
    Repositories,
)
from sircom2026.pipeline import (
    V1_INVALIDATION_DAG,
    V1_INVALIDATION_PARENTS,
    V1_WORKER_STEP_KEYS,
    downstream_step_keys,
    UnknownStepError,
)
from sircom2026.state import recompute_lot_status
from sircom2026.worker import enqueue_job


RETRYABLE_STEP_STATUSES = ("echoue", "bloque", "invalide")


@dataclass(frozen=True)
class InvalidationResult:
    source_step_key: str
    invalidated_steps: tuple[str, ...]
    obsolete_artifacts_count: int
    canceled_jobs_count: int


@dataclass(frozen=True)
class InputChangeResult:
    source_step_key: str
    source_fingerprint: str
    invalidated_steps: tuple[str, ...]
    obsolete_artifacts_count: int
    canceled_jobs_count: int


@dataclass(frozen=True)
class HumanValidationSnapshot:
    step_key: str
    output_fingerprint: str
    invalidated_steps: tuple[str, ...]
    obsolete_artifacts_count: int
    canceled_jobs_count: int


@dataclass(frozen=True)
class RetryResult:
    job: dict[str, Any]
    job_created: bool
    run_id: str
    input_fingerprint: str
    invalidated_steps: tuple[str, ...]
    obsolete_artifacts_count: int
    canceled_jobs_count: int


class RetryNotAllowedError(ValueError):
    """Raised when a step cannot be retried from its current state."""


def fingerprint_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def step_input_fingerprint(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    input_payload: Mapping[str, Any] | None = None,
) -> str:
    _require_known_step(step_key)
    steps_by_key = {
        step["step_key"]: step for step in repositories.steps.list_for_lot(lot_id)
    }
    ordered_parents = [
        steps_by_key[parent_key]
        for parent_key in V1_INVALIDATION_PARENTS.get(step_key, ())
        if parent_key in steps_by_key
    ]
    return fingerprint_payload(
        {
            "kind": "step_input",
            "schema_version": 1,
            "step_key": step_key,
            "upstream": [
                {
                    "step_key": parent["step_key"],
                    "output_fingerprint": parent["output_fingerprint"],
                }
                for parent in ordered_parents
            ],
            "input": dict(input_payload or {}),
        }
    )


def invalidate_downstream(
    repositories: Repositories,
    *,
    lot_id: str,
    source_step_key: str,
    reason: str,
    run_id: str | None = None,
) -> InvalidationResult:
    _require_known_step(source_step_key)
    _require_mutable_lot(repositories, lot_id)

    invalidated_steps = downstream_step_keys(source_step_key)
    canceled_jobs_count = 0
    obsolete_artifacts_count = 0
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=invalidated_steps,
    )

    for step_key in invalidated_steps:
        canceled_jobs_count += repositories.jobs.cancel_active_for_step(
            lot_id, step_key
        )
        obsolete_for_step = repositories.artifacts.mark_obsolete_for_steps(
            lot_id=lot_id,
            step_keys=(step_key,),
        )
        obsolete_artifacts_count += obsolete_for_step
        repositories.steps.mark_invalidated(lot_id=lot_id, step_key=step_key)
        repositories.events.create(
            lot_id=lot_id,
            step_key=step_key,
            run_id=run_id,
            event_type="step.invalidated",
            payload={
                "artifacts_count": obsolete_for_step,
                "reason": reason,
                "source_step_key": source_step_key,
                "status": "invalide",
                "step_key": step_key,
            },
        )

    recompute_lot_status(repositories, lot_id)
    return InvalidationResult(
        source_step_key=source_step_key,
        invalidated_steps=invalidated_steps,
        obsolete_artifacts_count=obsolete_artifacts_count,
        canceled_jobs_count=canceled_jobs_count,
    )


def record_input_change(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    input_payload: Mapping[str, Any],
    reason: str,
) -> InputChangeResult:
    _require_known_step(step_key)
    _require_mutable_lot(repositories, lot_id)
    source_fingerprint = fingerprint_payload(
        {
            "kind": "input_change",
            "schema_version": 1,
            "step_key": step_key,
            "input": dict(input_payload),
        }
    )
    repositories.steps.set_output_fingerprint(
        lot_id=lot_id,
        step_key=step_key,
        output_fingerprint=source_fingerprint,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        event_type="step.input_changed",
        payload={
            "output_fingerprint": source_fingerprint,
            "reason": reason,
            "step_key": step_key,
        },
    )
    invalidation = invalidate_downstream(
        repositories,
        lot_id=lot_id,
        source_step_key=step_key,
        reason=reason,
    )
    return InputChangeResult(
        source_step_key=step_key,
        source_fingerprint=source_fingerprint,
        invalidated_steps=invalidation.invalidated_steps,
        obsolete_artifacts_count=invalidation.obsolete_artifacts_count,
        canceled_jobs_count=invalidation.canceled_jobs_count,
    )


def record_human_validation_snapshot(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    decision_payload: Mapping[str, Any],
    run_id: str | None = None,
    reason: str,
) -> HumanValidationSnapshot:
    _require_known_step(step_key)
    _require_mutable_lot(repositories, lot_id)
    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
    )
    output_fingerprint = fingerprint_payload(
        {
            "kind": "human_validation",
            "input_fingerprint": input_fingerprint,
            "schema_version": 1,
            "step_key": step_key,
            "decision": dict(decision_payload),
        }
    )
    repositories.steps.set_output_fingerprint(
        lot_id=lot_id,
        step_key=step_key,
        input_fingerprint=input_fingerprint,
        output_fingerprint=output_fingerprint,
        run_id=run_id,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        event_type="step.validation_snapshot_frozen",
        payload={
            "output_fingerprint": output_fingerprint,
            "reason": reason,
            "step_key": step_key,
        },
    )
    invalidation = invalidate_downstream(
        repositories,
        lot_id=lot_id,
        source_step_key=step_key,
        reason=reason,
        run_id=run_id,
    )
    return HumanValidationSnapshot(
        step_key=step_key,
        output_fingerprint=output_fingerprint,
        invalidated_steps=invalidation.invalidated_steps,
        obsolete_artifacts_count=invalidation.obsolete_artifacts_count,
        canceled_jobs_count=invalidation.canceled_jobs_count,
    )


def retry_step(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    idempotency_key: str,
    input_payload: Mapping[str, Any] | None = None,
) -> RetryResult:
    _require_known_step(step_key)
    _require_mutable_lot(repositories, lot_id)
    step = _require_step(repositories, lot_id, step_key)
    existing_job = repositories.jobs.get_by_idempotency_key(
        lot_id=lot_id,
        step_key=step_key,
        idempotency_key=idempotency_key,
    )
    if existing_job is not None:
        if (
            existing_job["status"] in ACTIVE_JOB_STATUSES
            and step["current_run_id"] == existing_job["run_id"]
        ):
            input_fingerprint = step["input_fingerprint"] or step_input_fingerprint(
                repositories,
                lot_id=lot_id,
                step_key=step_key,
                input_payload=input_payload,
            )
            return RetryResult(
                job=existing_job,
                job_created=False,
                run_id=existing_job["run_id"],
                input_fingerprint=input_fingerprint,
                invalidated_steps=(),
                obsolete_artifacts_count=0,
                canceled_jobs_count=0,
            )
        raise RetryNotAllowedError("Cette clé d'idempotence a déjà été consommée.")

    if step["status"] not in RETRYABLE_STEP_STATUSES:
        raise RetryNotAllowedError(
            "Cette étape ne peut pas être relancée dans son état courant."
        )
    if step_key not in V1_WORKER_STEP_KEYS:
        raise RetryNotAllowedError(
            "Cette étape attend une action utilisateur, pas un worker."
        )

    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        input_payload=input_payload,
    )
    new_run_id = f"run_{uuid.uuid4().hex}"
    source_canceled_jobs = repositories.jobs.cancel_active_for_step(lot_id, step_key)
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(step_key,),
    )
    invalidation = invalidate_downstream(
        repositories,
        lot_id=lot_id,
        source_step_key=step_key,
        reason="retry",
        run_id=new_run_id,
    )
    queued = enqueue_job(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        idempotency_key=idempotency_key,
        run_id=new_run_id,
        input_fingerprint=input_fingerprint,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=new_run_id,
        event_type="retry.requested",
        payload={
            "input_fingerprint": input_fingerprint,
            "invalidated_steps_count": len(invalidation.invalidated_steps),
            "obsolete_artifacts_count": invalidation.obsolete_artifacts_count,
            "run_id": new_run_id,
            "step_key": step_key,
        },
    )
    return RetryResult(
        job=queued.job,
        job_created=queued.created,
        run_id=new_run_id,
        input_fingerprint=input_fingerprint,
        invalidated_steps=invalidation.invalidated_steps,
        obsolete_artifacts_count=invalidation.obsolete_artifacts_count,
        canceled_jobs_count=source_canceled_jobs + invalidation.canceled_jobs_count,
    )


def _require_known_step(step_key: str) -> None:
    if step_key not in V1_INVALIDATION_DAG:
        raise UnknownStepError(f"Unknown step key: {step_key}.")


def _require_mutable_lot(repositories: Repositories, lot_id: str) -> dict[str, Any]:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise RetryNotAllowedError(
            "Le lot annulé ou supprimé ne peut plus être modifié."
        )
    return lot


def _require_step(
    repositories: Repositories,
    lot_id: str,
    step_key: str,
) -> dict[str, Any]:
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if step is None:
        raise KeyError(f"{lot_id}:{step_key}")
    return step
