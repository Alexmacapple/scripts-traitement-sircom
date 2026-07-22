from __future__ import annotations

import sqlite3
from typing import Any

from sircom2026.config import ConfigError, Settings
from sircom2026.csv_preview import CsvPreviewError, get_csv_preview_payload
from sircom2026.database import Database, SchemaVersionError
from sircom2026.image_matching import ImageMatchingNotReady, get_persisted_image_matching
from sircom2026.images import ImageInspectionNotReady, get_persisted_image_inspection
from sircom2026.lots import list_lots
from sircom2026.mapping import MappingError
from sircom2026.package import PackageNotReady, get_persisted_package
from sircom2026.purge import storage_summary
from sircom2026.reports import ReportsNotReady, get_persisted_reports
from sircom2026.sorting import SortDecisionError, get_sort_payload
from sircom2026.web_ui import (
    image_matching_ui_payload,
    lot_sources_summary,
    lot_ui_summary,
    mapping_ui_error,
    sort_ui_payload,
    ui_error,
)


def _app_facade():
    from sircom2026 import app as app_facade

    return app_facade


def load_index_context(
    settings: Settings,
    settings_error: ConfigError | None,
    lot_id: str | None,
    *,
    active_view_key: str | None = None,
    active_screen_key: str | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "lots": [],
        "selected_lot": None,
        "storage": None,
        "ui_error": None,
    }
    if settings_error is not None:
        context["ui_error"] = ui_error(
            "Configuration invalide",
            "La configuration locale ne peut pas être chargée.",
            "Corriger les variables SIRCOM_* puis relancer l'application.",
        )
        return context

    database = Database(
        settings.sqlite_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    try:
        database.migrate()
        with database.session() as repositories:
            storage = storage_summary(repositories, settings=settings)
            context["storage"] = storage
            storage_by_lot_id = {item["id"]: item for item in storage["lots"]}
            context["lots"] = list_lots(repositories, limit=20, offset=0)["items"]
            for lot_item in context["lots"]:
                lot_item["storage"] = storage_by_lot_id.get(lot_item["id"])
            if lot_id:
                try:
                    selected_lot = _app_facade().get_lot_detail(repositories, lot_id)
                    selected_lot["storage"] = storage_by_lot_id.get(lot_id)
                    try:
                        selected_lot["mapping"] = _app_facade().get_mapping_payload(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                    except MappingError as exc:
                        selected_lot["mapping"] = None
                        if exc.code != "SIRCOM_MAPPING_DIAGNOSTIC_NOT_READY":
                            selected_lot["mapping_error"] = mapping_ui_error(exc)
                    try:
                        selected_lot["sort"] = get_sort_payload(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                        selected_lot["sort"] = sort_ui_payload(selected_lot["sort"])
                    except SortDecisionError:
                        selected_lot["sort"] = None
                    try:
                        selected_lot["csv_preview"] = get_csv_preview_payload(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                    except CsvPreviewError:
                        selected_lot["csv_preview"] = None
                    try:
                        selected_lot["image_inspection"] = get_persisted_image_inspection(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        ).inspection
                    except ImageInspectionNotReady:
                        selected_lot["image_inspection"] = None
                    try:
                        image_matching = get_persisted_image_matching(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                        selected_lot["image_matching"] = {
                            "matching": image_matching_ui_payload(image_matching.matching),
                            "artifact": image_matching.artifact,
                            "processed_images_artifact": (
                                {
                                    **image_matching.processed_images_artifact,
                                    "download_url": (
                                        f"/api/lots/{lot_id}/downloads/"
                                        f"{image_matching.processed_images_artifact['id']}"
                                    ),
                                }
                                if image_matching.processed_images_artifact
                                else None
                            ),
                        }
                    except ImageMatchingNotReady:
                        selected_lot["image_matching"] = None
                    try:
                        reports = get_persisted_reports(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                        selected_lot["reports"] = {
                            "business_report_artifact": {
                                **reports.business_artifact,
                                "download_url": (
                                    f"/api/lots/{lot_id}/downloads/"
                                    f"{reports.business_artifact['id']}"
                                ),
                            },
                            "technical_report_artifact": {
                                **reports.technical_artifact,
                                "download_url": (
                                    f"/api/lots/{lot_id}/downloads/"
                                    f"{reports.technical_artifact['id']}"
                                ),
                            },
                        }
                    except ReportsNotReady:
                        selected_lot["reports"] = None
                    try:
                        package = get_persisted_package(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                        selected_lot["package"] = {
                            "artifact": {
                                **package.artifact,
                                "download_url": (
                                    f"/api/lots/{lot_id}/downloads/"
                                    f"{package.artifact['id']}"
                                ),
                            },
                        }
                    except PackageNotReady:
                        selected_lot["package"] = None
                    selected_lot["sources"] = lot_sources_summary(
                        repositories,
                        selected_lot,
                    )
                    selected_lot["ui"] = lot_ui_summary(
                        selected_lot,
                        active_view_key=active_view_key,
                        active_screen_key=active_screen_key,
                    )
                    context["selected_lot"] = selected_lot
                except KeyError:
                    context["ui_error"] = ui_error(
                        "Lot introuvable",
                        "Le lot demandé n'existe pas ou a été retiré.",
                        "Sélectionner un lot actif dans la liste.",
                    )
    except (OSError, SchemaVersionError, sqlite3.Error):
        context["ui_error"] = ui_error(
            "Base locale indisponible",
            "SQLite ne peut pas être ouvert ou migré.",
            "Vérifier le dossier de données puis relancer l'application.",
        )
    return context
