from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from sircom2026.api.dependencies import get_database
from sircom2026.api.errors import ArtifactHiddenReason, hidden_artifact_not_found
from sircom2026.api.security import AccessAction, ActorContext, require_action
from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError
from sircom2026.database import Database, Repositories


router = APIRouter(prefix="/api/lots/{lot_id}/downloads", tags=["artifacts"])


@router.get("/{artifact_id}", response_class=FileResponse)
async def download_artifact(
    lot_id: str,
    artifact_id: str,
    request: Request,
    _actor: Annotated[
        ActorContext, Depends(require_action(AccessAction.ARTIFACT_DOWNLOAD))
    ],
    database: Annotated[Database, Depends(get_database)],
) -> FileResponse:
    settings = request.app.state.settings
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    hidden_error = None
    readable = None
    with database.transaction() as repositories:
        reason = hidden_download_reason(repositories, lot_id, artifact_id)
        if reason is not None:
            hidden_error = hidden_artifact_not_found(
                lot_id=lot_id,
                artifact_id=artifact_id,
                reason=reason,
                request=request,
            )
        else:
            try:
                readable = store.open_for_read(
                    repositories,
                    lot_id=lot_id,
                    artifact_id=artifact_id,
                )
            except (ArtifactUnavailableError, KeyError, ValueError):
                hidden_error = hidden_artifact_not_found(
                    lot_id=lot_id,
                    artifact_id=artifact_id,
                    reason=ArtifactHiddenReason.OBSOLETE,
                    request=request,
                )

    if hidden_error is not None:
        raise hidden_error
    if readable is None:
        raise hidden_artifact_not_found(
            lot_id=lot_id,
            artifact_id=artifact_id,
            reason=ArtifactHiddenReason.ABSENT,
            request=request,
        )

    return FileResponse(
        readable.path,
        media_type=readable.media_type,
        filename=readable.filename,
    )


def hidden_download_reason(
    repositories: Repositories,
    lot_id: str,
    artifact_id: str,
) -> ArtifactHiddenReason | None:
    lot = repositories.lots.get(lot_id)
    artifact = repositories.artifacts.get(artifact_id)
    if lot is None or artifact is None:
        return ArtifactHiddenReason.ABSENT
    if artifact["lot_id"] != lot_id:
        return ArtifactHiddenReason.OTHER_LOT
    if lot["status"] in {"supprime", "purge"} or artifact["status"] == "deleted":
        return ArtifactHiddenReason.DELETED
    if artifact["status"] != "committed":
        return ArtifactHiddenReason.OBSOLETE
    return None
