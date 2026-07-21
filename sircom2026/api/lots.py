from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from pydantic import BaseModel, Field

from sircom2026.api.dependencies import get_database
from sircom2026.api.errors import ApiError
from sircom2026.api.security import AccessAction, ActorContext, require_action
from sircom2026.database import Database
from sircom2026.invalidation import RetryNotAllowedError, UnknownStepError, retry_step
from sircom2026.lots import create_lot_with_steps, get_lot_detail, list_lots, mark_lot_deleted


router = APIRouter(prefix="/api/lots", tags=["lots"])


class CreateLotRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class RetryStepRequest(BaseModel):
    step_key: str = Field(min_length=1, max_length=64)


@router.post("", status_code=201)
async def create_lot(
    response: Response,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_CREATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[CreateLotRequest | None, Body()] = None,
) -> dict[str, object]:
    creation_payload = payload or CreateLotRequest()
    with database.transaction() as repositories:
        lot = create_lot_with_steps(
            repositories,
            title=creation_payload.title,
            idempotency_key=idempotency_key_from_request(request),
        )

    response.headers["Location"] = f"/api/lots/{lot['id']}"
    return {"lot": lot}


@router.post("/{lot_id}/retry", status_code=202)
async def retry_lot_step(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[RetryStepRequest, Body()],
) -> dict[str, object]:
    idempotency_key = idempotency_key_from_request(request)
    if idempotency_key is None:
        idempotency_key = f"retry:{payload.step_key}:{uuid.uuid4().hex}"

    with database.transaction() as repositories:
        try:
            result = retry_step(
                repositories,
                lot_id=lot_id,
                step_key=payload.step_key,
                idempotency_key=idempotency_key,
            )
            lot = get_lot_detail(repositories, lot_id)
        except UnknownStepError as exc:
            raise ApiError(
                400,
                "SIRCOM_STEP_INVALID",
                "Etape inconnue.",
            ) from exc
        except RetryNotAllowedError as exc:
            raise ApiError(
                409,
                "SIRCOM_RETRY_NOT_ALLOWED",
                "Relance impossible pour cette etape.",
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    return {
        "lot": lot,
        "job": {
            "id": result.job["id"],
            "step_key": result.job["step_key"],
            "run_id": result.job["run_id"],
            "status": result.job["status"],
            "created": result.job_created,
        },
        "invalidated_steps": list(result.invalidated_steps),
        "obsolete_artifacts_count": result.obsolete_artifacts_count,
        "canceled_jobs_count": result.canceled_jobs_count,
    }


@router.get("")
async def read_lots(
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    with database.session() as repositories:
        return list_lots(
            repositories,
            limit=limit,
            offset=offset,
        )


@router.get("/{lot_id}")
async def read_lot(
    lot_id: str,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    with database.session() as repositories:
        try:
            lot = get_lot_detail(repositories, lot_id)
        except KeyError as exc:
            raise lot_not_found() from exc
    return {"lot": lot}


@router.delete("/{lot_id}")
async def delete_lot(
    lot_id: str,
    response: Response,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_DELETE))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    with database.transaction() as repositories:
        try:
            lot, active_job_count = mark_lot_deleted(repositories, lot_id)
        except KeyError as exc:
            raise lot_not_found() from exc

    if active_job_count:
        response.status_code = 202
    return {"lot": lot, "cancel_requested_jobs": active_job_count}


def lot_not_found() -> ApiError:
    return ApiError(
        404,
        "SIRCOM_LOT_NOT_FOUND",
        "Lot introuvable.",
    )


def idempotency_key_from_request(request: Request) -> str | None:
    raw_value = request.headers.get("x-idempotency-key")
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    if len(value) > 128:
        raise ApiError(
            400,
            "SIRCOM_IDEMPOTENCY_KEY_INVALID",
            "Cle d'idempotence invalide.",
        )
    return value
