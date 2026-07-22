from __future__ import annotations

import shutil

from fastapi import FastAPI

from sircom2026.api.security import AccessPolicy
from sircom2026.app_factory import create_app as _create_app
from sircom2026.app_lifecycle import (
    ReadinessCheck,
    check_readiness,
    periodic_purge_loop,
    periodic_worker_loop,
    reconcile_artifacts_at_startup,
)
from sircom2026.config import Settings, load_settings
from sircom2026.lots import get_lot_detail
from sircom2026.mapping import get_mapping_payload
from sircom2026.web_constants import (
    DSFR_ASSETS_PATH,
    DSFR_VERSION,
    STATIC_DIR,
    TEMPLATE_DIR,
    static_asset_version,
)
from sircom2026.web_context import load_index_context

__all__ = [
    "DSFR_ASSETS_PATH",
    "DSFR_VERSION",
    "ReadinessCheck",
    "STATIC_DIR",
    "TEMPLATE_DIR",
    "app",
    "check_readiness",
    "create_app",
    "get_lot_detail",
    "get_mapping_payload",
    "load_index_context",
    "load_settings",
    "periodic_purge_loop",
    "periodic_worker_loop",
    "reconcile_artifacts_at_startup",
    "shutil",
    "static_asset_version",
]


def create_app(
    settings: Settings | None = None,
    *,
    access_policy: AccessPolicy | None = None,
) -> FastAPI:
    return _create_app(
        settings,
        access_policy=access_policy,
        load_settings_func=load_settings,
    )


app = create_app()
