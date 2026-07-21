from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from sircom2026.api.dependencies import get_database
from sircom2026.api.security import AccessAction, ActorContext, require_action
from sircom2026.database import Database
from sircom2026.purge import storage_summary


router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("")
async def read_storage(
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.CONFIG_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.session() as repositories:
        return {"storage": storage_summary(repositories, settings=settings)}
