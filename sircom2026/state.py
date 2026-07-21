from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sircom2026.database import (
    PROBLEM_SEVERITIES,
    STEP_STATUSES,
    Repositories,
)


STEP_DONE_STATUSES = {"termine", "termine_avec_alertes", "ignore"}
LOT_PROTECTED_STATUSES = {"supprime", "purge"}
PROBLEM_EVENT_LEVELS = {
    "bloquant": "error",
    "alerte": "warning",
    "information": "info",
}
STEP_EVENT_LEVELS = {
    "bloque": "error",
    "echoue": "error",
    "termine_avec_alertes": "warning",
    "annule": "warning",
}


class StateTransitionError(ValueError):
    """Raised when a requested business transition would hide a required state."""


def record_problem(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    severity: str,
    code: str,
    title: str,
    cause: str,
    action: str,
    message: str | None = None,
    run_id: str | None = None,
    location: Mapping[str, Any] | None = None,
    technical: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if severity not in PROBLEM_SEVERITIES:
        allowed = ", ".join(PROBLEM_SEVERITIES)
        raise ValueError(f"Invalid problem severity: {severity!r}. Allowed values: {allowed}.")
    _require_step(repositories, lot_id, step_key)
    problem = repositories.problems.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        severity=severity,
        code=code,
        title=title,
        cause=cause,
        message=message or cause,
        action=action,
        location=location,
        technical=technical,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        level=PROBLEM_EVENT_LEVELS[severity],
        event_type="problem.recorded",
        payload={
            "code": code,
            "level": severity,
            "step_key": step_key,
        },
    )
    return problem


def transition_step(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    status: str,
    run_id: str | None = None,
    event_type: str = "step.status_changed",
) -> dict[str, Any]:
    if status not in STEP_STATUSES:
        allowed = ", ".join(STEP_STATUSES)
        raise ValueError(f"Invalid step status: {status!r}. Allowed values: {allowed}.")
    step = _require_step(repositories, lot_id, step_key)
    if status == "termine" and repositories.problems.count_open_for_step_by_severity(
        lot_id=lot_id,
        step_key=step_key,
        severity="alerte",
    ):
        raise StateTransitionError(
            "Une etape avec alerte ouverte doit etre marquee termine_avec_alertes."
        )

    updated_step = repositories.steps.update_status(step["id"], status, run_id=run_id)
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        level=STEP_EVENT_LEVELS.get(status, "info"),
        event_type=event_type,
        payload={
            "status": status,
            "step_key": step_key,
            "run_id": run_id,
        },
    )
    recompute_lot_status(repositories, lot_id)
    return updated_step


def complete_step(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    run_id: str | None = None,
    with_warnings: bool = False,
) -> dict[str, Any]:
    status = "termine_avec_alertes" if with_warnings else "termine"
    return transition_step(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        status=status,
        run_id=run_id,
        event_type="step.completed",
    )


def require_human_validation(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    return transition_step(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        status="action_requise",
        run_id=run_id,
        event_type="step.validation_required",
    )


def block_step(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    code: str,
    title: str,
    cause: str,
    action: str,
    run_id: str | None = None,
    location: Mapping[str, Any] | None = None,
    technical: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record_problem(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        severity="bloquant",
        code=code,
        title=title,
        cause=cause,
        action=action,
        location=location,
        technical=technical,
    )
    return transition_step(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        status="bloque",
        run_id=run_id,
        event_type="step.blocked",
    )


def fail_step(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    code: str,
    title: str,
    cause: str,
    action: str,
    run_id: str | None = None,
    technical: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record_problem(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        severity="bloquant",
        code=code,
        title=title,
        cause=cause,
        action=action,
        technical=technical,
    )
    return transition_step(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        status="echoue",
        run_id=run_id,
        event_type="step.failed",
    )


def cancel_active_step(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    step = _require_step(repositories, lot_id, step_key)
    canceled_jobs = repositories.jobs.cancel_active_for_step(lot_id, step_key)
    updated_step = repositories.steps.update_status(step["id"], "annule", run_id=run_id)
    repositories.lots.update_status(lot_id, "annule")
    repositories.events.create(
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        level="warning",
        event_type="step.canceled",
        payload={
            "active_jobs": canceled_jobs,
            "status": "annule",
            "step_key": step_key,
            "run_id": run_id,
        },
    )
    return updated_step


def recompute_lot_status(repositories: Repositories, lot_id: str) -> dict[str, Any]:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_PROTECTED_STATUSES:
        return lot

    steps = repositories.steps.list_for_lot(lot_id)
    step_statuses = {step["status"] for step in steps}

    if "annule" in step_statuses:
        status = "annule"
    elif "echoue" in step_statuses:
        status = "echoue"
    elif "bloque" in step_statuses or repositories.problems.count_open_by_severity(
        lot_id=lot_id,
        severity="bloquant",
    ):
        status = "bloque"
    elif "action_requise" in step_statuses:
        status = "action_requise"
    elif steps and all(step["status"] in STEP_DONE_STATUSES for step in steps):
        has_alerts = "termine_avec_alertes" in step_statuses or bool(
            repositories.problems.count_open_by_severity(
                lot_id=lot_id,
                severity="alerte",
            )
        )
        status = "termine_avec_alertes" if has_alerts else "termine"
    elif step_statuses & {"pret", "en_cours", "termine", "termine_avec_alertes", "ignore", "invalide"}:
        status = "en_cours"
    else:
        status = "brouillon"

    if status == lot["status"]:
        return lot
    return repositories.lots.update_status(lot_id, status)


def _require_step(repositories: Repositories, lot_id: str, step_key: str) -> dict[str, Any]:
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if step is None:
        raise KeyError(f"{lot_id}:{step_key}")
    return step
