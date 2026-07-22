from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from sircom2026 import __version__
from sircom2026.api.errors import ApiError
from sircom2026.api.security import AccessAction, ActorContext, require_action
from sircom2026.app_lifecycle import check_readiness
from sircom2026.web_constants import (
    DSFR_ASSETS_PATH,
    DSFR_VERSION,
    INFO_PAGES,
    WORKFLOW_SCREEN_BY_KEY,
    static_asset_version,
    templates,
)
from sircom2026.web_context import load_index_context
from sircom2026.web_ui import (
    lot_sources_href,
    lot_view_href,
    screen_key_for_step,
    upload_confirmation,
)


def register_web_routes(app: FastAPI) -> None:
    def render_app_page(
        request: Request,
        *,
        page_mode: str,
        lot_id: str | None,
        active_view_key: str | None = None,
        active_screen_key: str | None = None,
        uploaded: str | None = None,
    ):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": "Sircom 2026",
                "app_version": __version__,
                "static_asset_version": static_asset_version(),
                "dsfr_assets_path": DSFR_ASSETS_PATH,
                "dsfr_version": DSFR_VERSION,
                "limits": app.state.settings.public_limits(),
                "page_mode": page_mode,
                "upload_confirmation": upload_confirmation(uploaded),
                **load_index_context(
                    app.state.settings,
                    app.state.settings_error,
                    lot_id,
                    active_view_key=active_view_key,
                    active_screen_key=active_screen_key,
                ),
            },
        )

    @app.get("/", include_in_schema=False)
    async def index(
        request: Request,
        _actor: ActorContext = Depends(require_action(AccessAction.LOT_READ)),
    ):
        lot_id = request.query_params.get("lot_id")
        active_view_key = request.query_params.get("view")
        uploaded = request.query_params.get("uploaded")
        if lot_id and active_view_key and active_view_key not in {"upload_excel", "upload_images"}:
            return RedirectResponse(
                lot_view_href(lot_id, active_view_key),
                status_code=303,
            )
        return render_app_page(
            request,
            page_mode="sources",
            lot_id=lot_id,
            active_view_key=active_view_key,
            uploaded=uploaded,
        )

    @app.get("/lots/{lot_id}", include_in_schema=False)
    async def lot_workflow(
        request: Request,
        lot_id: str,
        _actor: ActorContext = Depends(require_action(AccessAction.LOT_READ)),
    ):
        active_view_key = request.query_params.get("view")
        if active_view_key in {"upload_excel", "upload_images"}:
            anchor = "excel-file" if active_view_key == "upload_excel" else "image-zip-file"
            return RedirectResponse(lot_sources_href(lot_id, anchor), status_code=303)
        if active_view_key:
            return RedirectResponse(lot_view_href(lot_id, active_view_key), status_code=303)
        return render_app_page(
            request,
            page_mode="workflow",
            lot_id=lot_id,
            active_view_key=active_view_key,
        )

    @app.get("/lots/{lot_id}/{workflow_screen}", include_in_schema=False)
    async def lot_workflow_screen(
        request: Request,
        lot_id: str,
        workflow_screen: str,
        _actor: ActorContext = Depends(require_action(AccessAction.LOT_READ)),
    ):
        if workflow_screen not in WORKFLOW_SCREEN_BY_KEY:
            raise HTTPException(status_code=404, detail="Not Found")
        active_view_key = request.query_params.get("view")
        if active_view_key and screen_key_for_step(active_view_key) != workflow_screen:
            return RedirectResponse(lot_view_href(lot_id, active_view_key), status_code=303)
        return render_app_page(
            request,
            page_mode="workflow",
            lot_id=lot_id,
            active_view_key=active_view_key,
            active_screen_key=workflow_screen,
        )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "sircom2026", "version": __version__}

    @app.get("/health/ready", tags=["health"])
    async def health_ready() -> JSONResponse:
        payload = check_readiness(app.state.settings, app.state.settings_error)
        return JSONResponse(
            status_code=200 if payload["ready"] else 503,
            content=payload,
        )

    @app.get("/api/config/limits", tags=["config"])
    async def config_limits(
        _actor: ActorContext = Depends(require_action(AccessAction.CONFIG_READ)),
    ) -> dict[str, object]:
        if app.state.settings_error is not None:
            raise ApiError(
                500,
                "SIRCOM_CONFIG_INVALID",
                "Configuration invalide.",
            )
        return {"limits": app.state.settings.public_limits()}

    @app.get("/{page_slug}", include_in_schema=False)
    async def information_page(request: Request, page_slug: str):
        page = INFO_PAGES.get(page_slug)
        if page is None:
            raise HTTPException(status_code=404, detail="Not Found")
        return templates.TemplateResponse(
            request,
            "info.html",
            {
                "app_name": "Sircom 2026",
                "app_version": __version__,
                "static_asset_version": static_asset_version(),
                "dsfr_assets_path": DSFR_ASSETS_PATH,
                "dsfr_version": DSFR_VERSION,
                "page": page,
            },
        )
