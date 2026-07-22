from __future__ import annotations

import sqlite3

from fastapi import Request

from sircom2026.api.errors import ApiError
from sircom2026.database import Database, SchemaVersionError


def get_database(request: Request) -> Database:
    if request.app.state.settings_error is not None:
        raise ApiError(
            500,
            "SIRCOM_CONFIG_INVALID",
            "Configuration invalide.",
        )

    settings = request.app.state.settings
    database = Database(
        settings.sqlite_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    if not getattr(request.app.state, "database_migrated", False):
        try:
            database.migrate()
        except (OSError, SchemaVersionError, sqlite3.Error) as exc:
            raise ApiError(
                500,
                "SIRCOM_DATABASE_UNAVAILABLE",
                "Base locale indisponible.",
            ) from exc
        request.app.state.database_migrated = True
    return database
