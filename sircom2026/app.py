from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sqlite3
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sircom2026 import __version__
from sircom2026.api.artifacts import router as artifacts_router
from sircom2026.api.errors import ApiError, register_error_handlers
from sircom2026.api.storage import router as storage_router
from sircom2026.api.security import (
    AccessAction,
    AccessPolicy,
    ActorContext,
    LocalAccessPolicy,
    require_action,
)
from sircom2026.api.lots import router as lots_router
from sircom2026.artifacts import ArtifactStore
from sircom2026.config import ConfigError, Settings, load_settings
from sircom2026.csv_preview import CsvPreviewError, get_csv_preview_payload
from sircom2026.database import Database, SchemaVersionError, connect_sqlite
from sircom2026.image_matching import ImageMatchingNotReady, get_persisted_image_matching
from sircom2026.images import ImageInspectionNotReady, get_persisted_image_inspection
from sircom2026.lots import get_lot_detail, list_lots
from sircom2026.mapping import MappingError, get_mapping_payload
from sircom2026.package import PackageNotReady, get_persisted_package
from sircom2026.purge import (
    format_bytes,
    purge_expired_lots,
    purge_expired_lots_for_settings,
    storage_summary,
)
from sircom2026.reports import ReportsNotReady, get_persisted_reports
from sircom2026.sorting import SortDecisionError, get_sort_payload
from sircom2026.worker_runner import run_worker_once


TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
DSFR_VERSION = "1.14.4"
DSFR_ASSETS_PATH = f"/static/dsfr/{DSFR_VERSION}"
LOGGER = logging.getLogger(__name__)
UI_DONE_STEP_STATUSES = {"termine", "termine_avec_alertes", "ignore"}
UI_IDLE_STEP_STATUSES = {"non_demarre", "invalide"}
UI_PENDING_STEP_STATUSES = {"pret", "en_cours"}
CSV_WORKFLOW_STEP_KEYS = {
    "fusion_multi_onglets",
    "normalisation_contenu",
    "tri_region_departement",
    "verification_csv_indesign",
    "previsualisation_csv",
}
IMAGE_WORKFLOW_STEP_KEYS = {
    "upload_images",
    "inspection_images",
    "matching_images",
}


def static_asset_version() -> str:
    asset_paths = (STATIC_DIR / "sircom.css", STATIC_DIR / "app.js")
    mtimes = [path.stat().st_mtime_ns for path in asset_paths if path.exists()]
    return str(max(mtimes)) if mtimes else __version__


UX_PHASE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "sources",
        "label": "Déposer les sources",
        "anchor": "lot-actions-title",
        "description": "Excel et zip images.",
        "step_keys": ("upload_excel", "upload_images"),
    },
    {
        "key": "diagnostic",
        "label": "Vérifier l'Excel",
        "anchor": "excel-diagnostic-title",
        "description": "Structure, en-têtes et points bloquants.",
        "step_keys": ("diagnostic_excel",),
    },
    {
        "key": "mapping",
        "label": "Choisir les colonnes",
        "anchor": "mapping-step-title",
        "description": "Champs exportés et noms CSV.",
        "step_keys": ("mapping",),
    },
    {
        "key": "csv",
        "label": "Contrôler le CSV",
        "anchor": "csv-workflow-title",
        "description": "Fusion, tri, normalisation et aperçu.",
        "step_keys": (
            "fusion_multi_onglets",
            "normalisation_contenu",
            "tri_region_departement",
            "verification_csv_indesign",
            "previsualisation_csv",
        ),
    },
    {
        "key": "images",
        "label": "Traiter les images",
        "anchor": "image-workflow-title",
        "description": "Inspection, association et export JPG.",
        "step_keys": ("inspection_images", "matching_images"),
    },
    {
        "key": "deliverables",
        "label": "Récupérer les livrables",
        "anchor": "reports-title",
        "description": "Rapports et package final.",
        "step_keys": ("rapports", "package_final"),
    },
)
STEP_NAV_ANCHORS = {
    "upload_excel": "lot-actions-title",
    "diagnostic_excel": "excel-diagnostic-title",
    "mapping": "mapping-step-title",
    "fusion_multi_onglets": "csv-workflow-title",
    "normalisation_contenu": "csv-workflow-title",
    "tri_region_departement": "csv-workflow-title",
    "verification_csv_indesign": "csv-workflow-title",
    "previsualisation_csv": "csv-workflow-title",
    "upload_images": "lot-actions-title",
    "inspection_images": "image-workflow-title",
    "matching_images": "image-workflow-title",
    "rapports": "reports-title",
    "package_final": "package-title",
}
UI_STEP_STATUS_PRESENTATION = {
    "non_demarre": {"ui_status_label": "À venir", "ui_badge_class": "info"},
    "pret": {"ui_status_label": "En attente", "ui_badge_class": "info"},
    "en_cours": {"ui_status_label": "En cours", "ui_badge_class": "info"},
    "action_requise": {"ui_status_label": "Action requise", "ui_badge_class": "warning"},
    "bloque": {"ui_status_label": "À corriger", "ui_badge_class": "error"},
    "termine": {"ui_status_label": "Terminé", "ui_badge_class": "success"},
    "termine_avec_alertes": {
        "ui_status_label": "Terminé avec alertes",
        "ui_badge_class": "warning",
    },
    "echoue": {"ui_status_label": "Erreur", "ui_badge_class": "error"},
    "ignore": {"ui_status_label": "Ignoré", "ui_badge_class": "info"},
    "annule": {"ui_status_label": "Annulé", "ui_badge_class": "warning"},
    "invalide": {"ui_status_label": "À refaire", "ui_badge_class": "warning"},
}
STEP_VIEW_DESCRIPTIONS = {
    "upload_excel": "Déposer uniquement le fichier Excel source du lot.",
    "diagnostic_excel": "Lire le résultat de contrôle de l'Excel avant le mapping.",
    "mapping": "Choisir les colonnes exportées et valider les noms CSV.",
    "fusion_multi_onglets": "Suivre la fusion à plat des onglets par id_dossier.",
    "normalisation_contenu": "Suivre le nettoyage des contenus avant export.",
    "tri_region_departement": "Valider l'ordre des lignes avant l'aperçu CSV.",
    "verification_csv_indesign": "Suivre la vérification du contrat CSV InDesign.",
    "previsualisation_csv": "Contrôler et valider l'aperçu du CSV final.",
    "upload_images": "Déposer uniquement le zip des images produit.",
    "inspection_images": "Lire le contrôle du zip images et des fichiers détectés.",
    "matching_images": "Contrôler les associations entre dossiers et images.",
    "rapports": "Récupérer les rapports métier et technique quand ils sont prêts.",
    "package_final": "Générer ou télécharger le package final.",
}
STEP_VIEW_GUIDANCE = {
    "upload_excel": {
        "user_action": "Sélectionner l'Excel, vérifier son nom, puis cliquer sur le bouton d'upload.",
        "system_action": "Le dépôt crée une tâche de diagnostic en arrière-plan.",
        "result": "Un message confirme la réception du fichier et l'étape diagnostic devient disponible.",
    },
    "diagnostic_excel": {
        "user_action": "Lire les blocages, alertes et informations avant de continuer.",
        "system_action": "Le worker contrôle les onglets, en-têtes, colonnes masquées, formules et id_dossier.",
        "result": "L'Excel est soit refusé avec corrections attendues, soit importable pour le mapping.",
    },
    "mapping": {
        "user_action": "Choisir les colonnes exportées, vérifier les rôles, puis valider le mapping.",
        "system_action": "L'application conserve la provenance sans afficher de valeurs métier.",
        "result": "Le mapping validé déclenche la préparation du CSV.",
    },
    "fusion_multi_onglets": {
        "user_action": "Surveiller l'état ; aucune saisie n'est attendue.",
        "system_action": "Le worker fusionne les onglets à plat par id_dossier.",
        "result": "Une table consolidée est prête pour normalisation.",
    },
    "normalisation_contenu": {
        "user_action": "Surveiller l'état ; aucune saisie n'est attendue.",
        "system_action": "Le worker nettoie les textes, dates, retours ligne et cellules vides.",
        "result": "Les contenus sont prêts pour le contrat CSV InDesign.",
    },
    "tri_region_departement": {
        "user_action": "Confirmer le tri s'il est proposé ; sinon conserver l'ordre source ou corriger le mapping.",
        "system_action": "L'application vérifie les rôles région et département issus du mapping.",
        "result": "L'ordre retenu est enregistré avant l'aperçu CSV.",
    },
    "verification_csv_indesign": {
        "user_action": "Surveiller l'état ; aucune saisie n'est attendue.",
        "system_action": "Le worker vérifie le format UTF-16, les colonnes image et le contrat d'export.",
        "result": "Le CSV est prêt à être prévisualisé.",
    },
    "previsualisation_csv": {
        "user_action": "Contrôler l'aperçu puis valider explicitement le CSV.",
        "system_action": "L'application montre les en-têtes, lignes et suppressions sans exposer de données sensibles inutiles.",
        "result": "La validation autorise la suite images et livrables.",
    },
    "upload_images": {
        "user_action": "Sélectionner le zip images, vérifier son nom, puis cliquer sur le bouton d'upload.",
        "system_action": "Le dépôt crée une tâche d'inspection du zip en arrière-plan.",
        "result": "Un message confirme la réception du zip et l'inspection devient disponible.",
    },
    "inspection_images": {
        "user_action": "Lire le contrôle du zip et vérifier les images détectées.",
        "system_action": "Le worker inspecte la racine du zip, les formats, tailles et entrées ignorées.",
        "result": "Les images inspectées sont prêtes pour l'association aux dossiers.",
    },
    "matching_images": {
        "user_action": "Résoudre les ambiguïtés puis valider chaque association demandée.",
        "system_action": "Le worker renomme, convertit et prépare les JPG finaux.",
        "result": "Les images finales sont disponibles pour le package.",
    },
    "rapports": {
        "user_action": "Télécharger ou vérifier les rapports disponibles.",
        "system_action": "L'application sépare rapport métier et capsule technique sans valeurs métier.",
        "result": "Les informations de suivi sont prêtes avant génération du package.",
    },
    "package_final": {
        "user_action": "Générer le package final ou télécharger le package existant.",
        "system_action": "Le worker assemble CSV, images, rapports et manifeste.",
        "result": "Un zip final compatible avec la chaîne InDesign est disponible.",
    },
}
INFO_PAGES = {
    "plan-du-site": {
        "title": "Plan du site",
        "lead": "Accès aux principales pages de l'application locale.",
        "callout_title": "Navigation disponible",
        "callout_text": (
            "Le parcours métier principal se trouve sur l'accueil. Les liens API "
            "et Santé restent en pied de page pour les besoins techniques."
        ),
        "links": [
            {"label": "Accueil", "href": "/"},
            {"label": "API", "href": "/docs"},
            {"label": "Santé", "href": "/health"},
        ],
    },
    "accessibilite": {
        "title": "Accessibilité",
        "lead": "Statut d'accessibilité à formaliser avant toute publication.",
        "callout_title": "Statut non audité",
        "callout_text": (
            "Aucun audit RGAA complet n'a été réalisé sur cette application locale. "
            "L'interface utilise des composants DSFR et doit être auditée avant exposition publique."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
    "mentions-legales": {
        "title": "Mentions légales",
        "lead": "Mentions à finaliser avec le responsable de publication.",
        "callout_title": "Prototype local",
        "callout_text": (
            "Cette page évite une impasse de navigation. Les mentions définitives "
            "devront être renseignées avant publication hors poste local."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
    "donnees-personnelles": {
        "title": "Données personnelles",
        "lead": "Traitement local des lots Sircom 2026.",
        "callout_title": "Données stockées localement",
        "callout_text": (
            "Les fichiers déposés et artefacts de lot restent stockés dans le répertoire "
            "local configuré. Les rapports techniques ne doivent pas exposer de valeurs métier."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
    "gestion-cookies": {
        "title": "Gestion des cookies",
        "lead": "Gestion à confirmer avant publication.",
        "callout_title": "Aucun consentement configuré",
        "callout_text": (
            "La V1 locale ne configure pas de bannière de consentement. Toute mesure "
            "d'audience ou publication future devra préciser la politique cookies."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
}

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    ok: bool
    code: str
    details: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"name": self.name, "ok": self.ok, "code": self.code}
        if self.details:
            payload["details"] = self.details
        return payload


def create_app(
    settings: Settings | None = None,
    *,
    access_policy: AccessPolicy | None = None,
) -> FastAPI:
    settings_error: ConfigError | None = None
    if settings is None:
        try:
            settings = load_settings()
        except ConfigError as exc:
            settings_error = exc
            settings = load_settings({})

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        reconcile_artifacts_at_startup(settings, settings_error)
        purge_task: asyncio.Task[None] | None = None
        worker_task: asyncio.Task[None] | None = None
        if settings_error is None:
            purge_task = asyncio.create_task(periodic_purge_loop(settings))
            if settings.worker_enabled:
                worker_task = asyncio.create_task(periodic_worker_loop(settings))
        try:
            yield
        finally:
            for task in (purge_task, worker_task):
                if task is not None:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task

    app = FastAPI(
        title="Sircom 2026",
        version=__version__,
        description="Socle local de l'application Sircom 2026.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.settings_error = settings_error
    app.state.access_policy = access_policy or LocalAccessPolicy(settings.bind_host)
    register_error_handlers(app)
    app.include_router(artifacts_router)
    app.include_router(lots_router)
    app.include_router(storage_router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def render_app_page(
        request: Request,
        *,
        page_mode: str,
        lot_id: str | None,
        active_view_key: str | None = None,
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
        return render_app_page(
            request,
            page_mode="workflow",
            lot_id=lot_id,
            active_view_key=active_view_key,
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

    return app


def reconcile_artifacts_at_startup(
    settings: Settings,
    settings_error: ConfigError | None,
) -> None:
    if settings_error is not None:
        return

    database = Database(
        settings.sqlite_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    try:
        database.migrate()
        with database.transaction() as repositories:
            expired_jobs = repositories.jobs.expire_stale_leases()
            report = store.reconcile(repositories)
            purge_outcomes = purge_expired_lots(repositories, settings=settings)
    except (OSError, SchemaVersionError, sqlite3.Error, ValueError):
        LOGGER.warning("technical_event=artifact_reconciliation_startup_failed", exc_info=True)
        return

    report_counts = report.to_dict()
    if expired_jobs or any(report_counts.values()) or purge_outcomes:
        LOGGER.info(
            "technical_event=artifact_reconciliation_startup counts=%s expired_jobs=%s purged=%s",
            report_counts,
            expired_jobs,
            len(purge_outcomes),
        )


async def periodic_purge_loop(settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.purge_interval_seconds)
        try:
            await asyncio.to_thread(purge_expired_lots_for_settings, settings)
        except (OSError, SchemaVersionError, sqlite3.Error, ValueError):
            LOGGER.warning("technical_event=periodic_purge_failed", exc_info=True)


async def periodic_worker_loop(settings: Settings) -> None:
    while True:
        try:
            result = await asyncio.to_thread(run_worker_once, settings=settings)
        except (OSError, SchemaVersionError, sqlite3.Error, ValueError):
            LOGGER.warning("technical_event=periodic_worker_failed", exc_info=True)
            await asyncio.sleep(settings.worker_poll_seconds)
            continue
        await asyncio.sleep(0 if result.processed else settings.worker_poll_seconds)


def check_readiness(
    settings: Settings,
    settings_error: ConfigError | None = None,
) -> dict[str, object]:
    checks: list[ReadinessCheck] = []

    if settings_error is not None:
        checks.append(ReadinessCheck("config", False, "SIRCOM_CONFIG_INVALID"))
        return _readiness_payload(checks)

    checks.append(ReadinessCheck("config", True, "SIRCOM_CONFIG_OK"))
    checks.append(_check_data_dir(settings))
    if checks[-1].ok:
        checks.append(_check_sqlite(settings))
        checks.append(_check_disk(settings))

    return _readiness_payload(checks)


def load_index_context(
    settings: Settings,
    settings_error: ConfigError | None,
    lot_id: str | None,
    *,
    active_view_key: str | None = None,
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
            "La configuration locale ne peut pas etre chargee.",
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
                    selected_lot = get_lot_detail(repositories, lot_id)
                    selected_lot["storage"] = storage_by_lot_id.get(lot_id)
                    try:
                        selected_lot["mapping"] = get_mapping_payload(
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
                            "matching": image_matching.matching,
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
                    )
                    context["selected_lot"] = selected_lot
                except KeyError:
                    context["ui_error"] = ui_error(
                        "Lot introuvable",
                        "Le lot demande n'existe pas ou a ete retire.",
                        "Selectionner un lot actif dans la liste.",
                    )
    except (OSError, SchemaVersionError, sqlite3.Error):
        context["ui_error"] = ui_error(
            "Base locale indisponible",
            "SQLite ne peut pas etre ouvert ou migre.",
            "Verifier le dossier de donnees puis relancer l'application.",
        )
    return context


def lot_ui_summary(
    lot: dict[str, Any],
    *,
    active_view_key: str | None = None,
) -> dict[str, Any]:
    steps = list(lot.get("steps") or [])
    total = len(steps)
    if not steps:
        return {
            "breadcrumb_label": "Lot",
            "completed": False,
            "current_step": None,
            "current_step_number": 0,
            "current_phase": None,
            "current_phase_number": 0,
            "active_phase": None,
            "active_step": None,
            "active_view_key": None,
            "csv_workflow_steps": [],
            "image_workflow_steps": [],
            "next_step": None,
            "next_phase": None,
            "previous_view_step": None,
            "next_view_step": None,
            "phase_total": 0,
            "phase_navigation": [],
            "step_navigation": [],
            "steps_total": 0,
        }

    completed = all(step["status"] in UI_DONE_STEP_STATUSES for step in steps)
    current_index = (
        total - 1
        if completed
        else next(
            (
                index
                for index, step in enumerate(steps)
                if step["status"] not in UI_DONE_STEP_STATUSES
            ),
            total - 1,
        )
    )
    step_navigation = [
        step_navigation_item(
            step,
            index=index,
            current_index=current_index,
            completed=completed,
        )
        for index, step in enumerate(steps)
    ]
    current_step = None if completed else steps[current_index]
    current_step_key = current_step["key"] if current_step else None
    phase_navigation = build_phase_navigation(
        step_navigation,
        current_step_key=current_step_key,
    )
    current_phase = next(
        (phase for phase in phase_navigation if phase["is_current"]),
        None,
    )
    current_phase_number = (
        len(phase_navigation)
        if completed
        else current_phase["number"] if current_phase else 0
    )
    active_step = selected_active_step(
        step_navigation,
        active_view_key=active_view_key,
        current_step=step_navigation[current_index],
    )
    active_view_key = active_step["key"] if active_step else None
    step_navigation = enrich_step_navigation(
        step_navigation,
        lot_id=lot["id"],
        active_view_key=active_view_key,
    )
    active_step = next(
        (step for step in step_navigation if step["is_active_view"]),
        active_step,
    )
    previous_view_step, next_view_step = adjacent_view_steps(
        step_navigation,
        active_view_key=active_view_key,
    )
    next_phase = (
        None
        if completed or not current_phase_number or current_phase_number >= len(phase_navigation)
        else phase_navigation[current_phase_number]
    )
    csv_workflow_steps = [
        step for step in step_navigation if step["key"] in CSV_WORKFLOW_STEP_KEYS
    ]
    image_workflow_steps = [
        step for step in step_navigation if step["key"] in IMAGE_WORKFLOW_STEP_KEYS
    ]
    return {
        "breadcrumb_label": (
            active_step["label"]
            if active_step
            else "Traitement terminé"
            if completed
            else current_step["label"]
        ),
        "completed": completed,
        "current_step": current_step,
        "current_step_number": current_index + 1,
        "current_phase": current_phase,
        "current_phase_number": current_phase_number,
        "active_step": active_step,
        "active_phase": current_phase,
        "active_view_key": active_view_key,
        "csv_workflow_started": workflow_started(csv_workflow_steps),
        "csv_workflow_steps": csv_workflow_steps,
        "image_workflow_started": workflow_started(image_workflow_steps),
        "image_workflow_steps": image_workflow_steps,
        "next_step": (
            None
            if completed or current_index + 1 >= total
            else steps[current_index + 1]
        ),
        "next_phase": next_phase,
        "previous_view_step": previous_view_step,
        "next_view_step": next_view_step,
        "phase_total": len(phase_navigation),
        "phase_navigation": phase_navigation,
        "primary_action": lot_primary_action(
            lot,
            current_step=current_step,
            current_phase=current_phase,
            completed=completed,
        ),
        "step_navigation": step_navigation,
        "steps_total": total,
    }


def selected_active_step(
    step_navigation: list[dict[str, Any]],
    *,
    active_view_key: str | None,
    current_step: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if active_view_key:
        requested = next(
            (step for step in step_navigation if step["key"] == active_view_key),
            None,
        )
        if requested:
            return requested
    if current_step:
        return current_step
    return step_navigation[0] if step_navigation else None


def enrich_step_navigation(
    step_navigation: list[dict[str, Any]],
    *,
    lot_id: str,
    active_view_key: str | None,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for step in step_navigation:
        view_key = step["key"]
        enriched.append(
            {
                **step,
                "href": step_href(lot_id, view_key),
                "is_active_view": view_key == active_view_key,
            }
        )
    return enriched


def adjacent_view_steps(
    step_navigation: list[dict[str, Any]],
    *,
    active_view_key: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not active_view_key:
        return None, None
    active_index = next(
        (
            index
            for index, step in enumerate(step_navigation)
            if step["key"] == active_view_key
        ),
        None,
    )
    if active_index is None:
        return None, None
    previous_step = step_navigation[active_index - 1] if active_index > 0 else None
    next_step = (
        step_navigation[active_index + 1]
        if active_index + 1 < len(step_navigation)
        else None
    )
    return previous_step, next_step


def step_navigation_item(
    step: dict[str, Any],
    *,
    index: int,
    current_index: int,
    completed: bool,
) -> dict[str, Any]:
    is_current = not completed and index == current_index
    is_done = step["status"] in UI_DONE_STEP_STATUSES
    is_future = not completed and index > current_index
    presentation = step_status_presentation(
        step["status"],
        is_current=is_current,
        is_future=is_future,
    )
    return {
        **step,
        "anchor": STEP_NAV_ANCHORS.get(step["key"], "timeline-title"),
        "is_current": is_current,
        "is_done": is_done,
        "is_future": is_future,
        "number": index + 1,
        "ui_description": STEP_VIEW_DESCRIPTIONS.get(
            step["key"],
            "Suivre cette étape du traitement.",
        ),
        "ui_guidance": STEP_VIEW_GUIDANCE.get(
            step["key"],
            {
                "user_action": "Suivre l'état de cette étape.",
                "system_action": "L'application orchestre le traitement prévu.",
                "result": "Le lot avance vers l'étape suivante.",
            },
        ),
        **presentation,
    }


def step_status_presentation(
    status: str,
    *,
    is_current: bool,
    is_future: bool,
) -> dict[str, str]:
    if status == "invalide" and is_future:
        return {"ui_status_label": "À venir", "ui_badge_class": "info"}
    if status == "invalide" and not is_current:
        return {"ui_status_label": "À venir", "ui_badge_class": "info"}
    return UI_STEP_STATUS_PRESENTATION.get(
        status,
        {"ui_status_label": status, "ui_badge_class": "info"},
    )


def workflow_started(steps: list[dict[str, Any]]) -> bool:
    return any(step["status"] not in UI_IDLE_STEP_STATUSES for step in steps)


def build_phase_navigation(
    steps: list[dict[str, Any]],
    *,
    current_step_key: str | None,
) -> list[dict[str, Any]]:
    steps_by_key = {step["key"]: step for step in steps}
    phases: list[dict[str, Any]] = []
    for index, definition in enumerate(UX_PHASE_DEFINITIONS, start=1):
        phase_steps = [
            steps_by_key[step_key]
            for step_key in definition["step_keys"]
            if step_key in steps_by_key
        ]
        status = phase_status(phase_steps)
        is_current = current_step_key in definition["step_keys"]
        if is_current and status["status_label"] == "À venir":
            status = {"status_label": "À faire maintenant", "badge_class": "info"}
        phases.append(
            {
                "number": index,
                "key": definition["key"],
                "label": definition["label"],
                "anchor": definition["anchor"],
                "description": definition["description"],
                "is_current": is_current,
                **status,
            }
        )
    return phases


def lot_primary_action(
    lot: dict[str, Any],
    *,
    current_step: dict[str, Any] | None,
    current_phase: dict[str, Any] | None,
    completed: bool,
) -> dict[str, str] | None:
    lot_id = lot["id"]
    if completed:
        return action_link(
            "Télécharger ou vérifier les livrables",
            lot_view_href(lot_id, "package_final", "package-title"),
            "fr-icon-download-line",
            "Les livrables disponibles sont dans la dernière section.",
        )
    if current_step is None:
        return None

    key = current_step["key"]
    status = current_step["status"]
    phase_label = current_phase["label"] if current_phase else current_step["label"]

    if status in UI_PENDING_STEP_STATUSES:
        return action_link(
            f"Actualiser l'état : {phase_label}",
            lot_view_href(
                lot_id,
                view_key_for_step(key),
                STEP_NAV_ANCHORS.get(key, "lot-detail-title"),
            ),
            "fr-icon-refresh-line",
            "Le traitement local tourne en arrière-plan ; l'actualisation montre le dernier état connu.",
        )
    if status in {"bloque", "echoue"} and key in {"diagnostic_excel", "upload_excel"}:
        return action_link(
            "Ouvrir le dépôt Excel",
            lot_sources_href(lot_id, "excel-file"),
            "fr-icon-upload-line",
            "Corriger le fichier puis redéposer l'Excel source.",
        )
    if status in {"bloque", "echoue"}:
        return action_link(
            "Voir les problèmes à corriger",
            lot_view_href(lot_id, key, "lot-problems-title"),
            "fr-icon-error-line",
            "Corriger la cause indiquée avant de continuer.",
        )
    if key == "upload_excel":
        return action_link(
            "Ouvrir le dépôt Excel source",
            lot_sources_href(lot_id, "excel-file"),
            "fr-icon-upload-line",
            "Le diagnostic Excel démarre après le dépôt.",
        )
    if key == "mapping":
        return action_link(
            "Ouvrir le mapping",
            lot_view_href(lot_id, "mapping", "mapping-step-title"),
            "fr-icon-arrow-right-line",
            "Choisir les colonnes exportées puis valider.",
        )
    if key == "tri_region_departement":
        return action_link(
            "Ouvrir le tri région/département",
            lot_view_href(lot_id, "tri_region_departement", "sort-title"),
            "fr-icon-arrow-right-line",
            "Valider l'ordre des lignes avant l'aperçu CSV.",
        )
    if key == "previsualisation_csv":
        return action_link(
            "Ouvrir l'aperçu CSV",
            lot_view_href(lot_id, "previsualisation_csv", "csv-preview-title"),
            "fr-icon-arrow-right-line",
            "Vérifier l'aperçu avant de produire les livrables.",
        )
    if key == "upload_images":
        return action_link(
            "Ouvrir le dépôt du zip images",
            lot_sources_href(lot_id, "image-zip-file"),
            "fr-icon-upload-line",
            "Le traitement images démarre après le dépôt du zip.",
        )
    if key == "matching_images":
        return action_link(
            "Ouvrir les associations images",
            lot_view_href(lot_id, "matching_images", "image-matching-title"),
            "fr-icon-arrow-right-line",
            "Résoudre les ambiguïtés si l'application en détecte.",
        )
    if key == "package_final":
        return action_link(
            "Ouvrir le package final",
            lot_view_href(lot_id, "package_final", "package-title"),
            "fr-icon-arrow-right-line",
            "Assembler le CSV, les images et les rapports dans un zip final.",
        )
    return action_link(
        f"Continuer vers : {phase_label}",
        lot_view_href(
            lot_id,
            view_key_for_step(key),
            STEP_NAV_ANCHORS.get(key, "lot-detail-title"),
        ),
        "fr-icon-arrow-right-line",
        "Ouvrir la section concernée.",
    )


def lot_view_href(lot_id: str, view_key: str, anchor: str | None = None) -> str:
    href = f"/lots/{quote(lot_id, safe='')}?view={quote(view_key, safe='')}"
    return f"{href}#{anchor}" if anchor else href


def lot_sources_href(lot_id: str, anchor: str | None = None) -> str:
    href = f"/?lot_id={quote(lot_id, safe='')}"
    return f"{href}#{anchor}" if anchor else href


def step_href(lot_id: str, view_key: str) -> str:
    if view_key == "upload_excel":
        return lot_sources_href(lot_id, "excel-file")
    if view_key == "upload_images":
        return lot_sources_href(lot_id, "image-zip-file")
    return lot_view_href(lot_id, view_key, "lot-workspace-title")


def view_key_for_step(step_key: str) -> str:
    return step_key


def action_link(label: str, href: str, icon_class: str, hint: str) -> dict[str, str]:
    return {
        "label": label,
        "href": href,
        "icon_class": icon_class,
        "hint": hint,
    }


def lot_sources_summary(repositories: Any, lot: dict[str, Any]) -> dict[str, Any]:
    steps_by_key = {step["key"]: step for step in lot.get("steps") or []}
    excel_artifact = current_source_artifact(
        repositories,
        lot_id=lot["id"],
        step_key="upload_excel",
    )
    images_artifact = current_source_artifact(
        repositories,
        lot_id=lot["id"],
        step_key="upload_images",
    )
    excel = source_card_summary(
        lot,
        kind="excel",
        title="Fichier Excel source",
        missing_status="À déposer",
        uploaded_status="Déposé",
        artifact=excel_artifact,
        upload_step=steps_by_key.get("upload_excel"),
        processing_step=steps_by_key.get("diagnostic_excel"),
        missing_action=action_link(
            "Aller au formulaire Excel",
            lot_sources_href(lot["id"], "excel-file"),
            "fr-icon-arrow-down-line",
            "Le diagnostic Excel démarre après le dépôt.",
        ),
        pending_action=action_link(
            "Actualiser l'état du diagnostic Excel",
            lot_view_href(lot["id"], "diagnostic_excel", "excel-diagnostic-title"),
            "fr-icon-refresh-line",
            "Le worker local traite le diagnostic en arrière-plan.",
        ),
        ready_action=action_link(
            "Continuer vers le mapping",
            lot_view_href(lot["id"], "mapping", "mapping-step-title"),
            "fr-icon-arrow-right-line",
            "Le fichier Excel est importable ; vérifier les colonnes à exporter.",
        ),
        blocked_action=action_link(
            "Redéposer un Excel corrigé",
            lot_sources_href(lot["id"], "excel-file"),
            "fr-icon-upload-line",
            "Corriger le fichier puis déposer une nouvelle version.",
        ),
    )
    images = source_card_summary(
        lot,
        kind="images",
        title="Zip images produit",
        missing_status="À déposer",
        uploaded_status="Déposé",
        artifact=images_artifact,
        upload_step=steps_by_key.get("upload_images"),
        processing_step=steps_by_key.get("inspection_images"),
        missing_action=action_link(
            "Aller au formulaire zip images",
            lot_sources_href(lot["id"], "image-zip-file"),
            "fr-icon-arrow-down-line",
            "L'inspection démarre après le dépôt du zip.",
        ),
        pending_action=action_link(
            "Actualiser l'état des images",
            lot_view_href(lot["id"], "inspection_images", "image-workflow-title"),
            "fr-icon-refresh-line",
            "Le worker local inspecte le zip en arrière-plan.",
        ),
        ready_action=action_link(
            "Voir le traitement images",
            lot_view_href(lot["id"], "matching_images", "image-matching-title"),
            "fr-icon-arrow-right-line",
            "Consulter l'inspection, les associations et les images traitées.",
        ),
        blocked_action=action_link(
            "Redéposer un zip images corrigé",
            lot_sources_href(lot["id"], "image-zip-file"),
            "fr-icon-upload-line",
            "Corriger le zip puis déposer une nouvelle version.",
        ),
    )
    image_inspection = lot.get("image_inspection")
    if images["uploaded"] and isinstance(image_inspection, dict):
        images["details"].append(("Images détectées", str(image_inspection.get("image_count", 0))))
        images["details"].append(("Entrées du zip", str(image_inspection.get("entries_count", 0))))
    return {
        "excel": excel,
        "images": images,
        "all_required_uploaded": bool(excel["uploaded"] and images["uploaded"]),
        "items": [excel, images],
    }


def source_card_summary(
    lot: dict[str, Any],
    *,
    kind: str,
    title: str,
    missing_status: str,
    uploaded_status: str,
    artifact: dict[str, Any] | None,
    upload_step: dict[str, Any] | None,
    processing_step: dict[str, Any] | None,
    missing_action: dict[str, str],
    pending_action: dict[str, str],
    ready_action: dict[str, str],
    blocked_action: dict[str, str],
) -> dict[str, Any]:
    uploaded = artifact is not None
    metadata = artifact_metadata(artifact) if artifact else {}
    details: list[tuple[str, str]] = []
    if uploaded and artifact is not None:
        details.append(("État du dépôt", uploaded_status))
        details.append(("Taille reçue", format_bytes(int(artifact["size_bytes"] or 0))))
        details.append(("Reçu le", format_datetime_label(str(artifact.get("created_at") or ""))))
        extension = metadata.get("extension")
        if isinstance(extension, str) and extension:
            details.append(("Format", extension))
        if kind == "excel":
            sheet_count = metadata.get("sheet_count")
            if isinstance(sheet_count, int):
                details.append(("Onglets détectés", str(sheet_count)))
        action = action_for_uploaded_source(
            processing_step=processing_step,
            pending_action=pending_action,
            ready_action=ready_action,
            blocked_action=blocked_action,
        )
        processing_label = source_processing_label(processing_step)
    else:
        details.append(("État du dépôt", missing_status))
        details.append(("Taille reçue", "Aucun fichier"))
        action = missing_action
        processing_label = "En attente du dépôt"

    return {
        "kind": kind,
        "title": title,
        "uploaded": uploaded,
        "status_label": uploaded_status if uploaded else missing_status,
        "badge_class": "success" if uploaded else "info",
        "upload_status_label": (
            upload_step["status_label"] if upload_step else "Non démarrée"
        ),
        "processing_label": processing_label,
        "details": details,
        "action": action,
    }


def action_for_uploaded_source(
    *,
    processing_step: dict[str, Any] | None,
    pending_action: dict[str, str],
    ready_action: dict[str, str],
    blocked_action: dict[str, str],
) -> dict[str, str]:
    status = processing_step["status"] if processing_step else "non_demarre"
    if status in UI_PENDING_STEP_STATUSES:
        return pending_action
    if status in {"bloque", "echoue"}:
        return blocked_action
    return ready_action


def source_processing_label(processing_step: dict[str, Any] | None) -> str:
    if processing_step is None:
        return "Traitement non démarré"
    status = processing_step["status"]
    if status == "pret":
        return "Traitement en attente"
    if status == "en_cours":
        return "Traitement en cours"
    if status in UI_DONE_STEP_STATUSES:
        return processing_step["status_label"]
    if status in {"bloque", "echoue"}:
        return "Correction attendue"
    return processing_step["status_label"]


def current_source_artifact(
    repositories: Any,
    *,
    lot_id: str,
    step_key: str,
) -> dict[str, Any] | None:
    row = repositories.connection.execute(
        """
        SELECT *
        FROM artefacts
        WHERE lot_id = ?
          AND step_key = ?
          AND role = 'source'
          AND status = 'committed'
        ORDER BY COALESCE(committed_at, created_at) DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (lot_id, step_key),
    ).fetchone()
    return dict(row) if row is not None else None


def artifact_metadata(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    value = artifact.get("metadata_json")
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def format_datetime_label(value: str) -> str:
    if not value:
        return "Date inconnue"
    return value.replace("T", " ").split("+", 1)[0].removesuffix("Z")


def phase_status(steps: list[dict[str, Any]]) -> dict[str, str]:
    statuses = {step["status"] for step in steps}
    if not steps:
        return {"status_label": "À venir", "badge_class": "info"}
    if statuses & {"bloque", "echoue"}:
        return {"status_label": "À corriger", "badge_class": "error"}
    if "action_requise" in statuses:
        return {"status_label": "Action requise", "badge_class": "warning"}
    if "en_cours" in statuses:
        return {"status_label": "En cours", "badge_class": "info"}
    if "pret" in statuses:
        return {"status_label": "Prêt", "badge_class": "info"}
    if all(status in UI_DONE_STEP_STATUSES for status in statuses):
        if "termine_avec_alertes" in statuses:
            return {"status_label": "Terminé avec alertes", "badge_class": "warning"}
        return {"status_label": "Terminé", "badge_class": "success"}
    if statuses & UI_DONE_STEP_STATUSES:
        return {"status_label": "Partiel", "badge_class": "info"}
    if statuses <= {"non_demarre", "invalide"}:
        return {"status_label": "À venir", "badge_class": "info"}
    return {"status_label": "À suivre", "badge_class": "info"}


def ui_error(title: str, cause: str, action: str) -> dict[str, str]:
    return {
        "title": title,
        "cause": cause,
        "action": action,
    }


def upload_confirmation(uploaded: str | None) -> dict[str, str] | None:
    if uploaded == "excel":
        return {
            "kind": "excel",
            "title": "Votre document a bien été uploadé",
            "cause": "Le fichier Excel source est reçu par le lot.",
            "action": "Attendre le diagnostic Excel, puis valider le mapping quand il apparaît.",
        }
    if uploaded == "images":
        return {
            "kind": "images",
            "title": "Votre document a bien été uploadé",
            "cause": "Le zip images produit est reçu par le lot.",
            "action": "Attendre l'inspection images, puis résoudre les associations si demandé.",
        }
    return None


def mapping_ui_error(exc: MappingError) -> dict[str, str]:
    if exc.code == "SIRCOM_MAPPING_SOURCE_HEADERS_MISSING":
        action = (
            "Relancer le diagnostic Excel ou redéposer l'Excel pour reconstruire "
            "les métadonnées de colonnes."
        )
    elif exc.code == "SIRCOM_MAPPING_DIAGNOSTIC_BLOCKED":
        action = "Corriger l'Excel bloquant puis redéposer le fichier."
    else:
        action = "Relancer l'étape précédente ou redéposer l'Excel."
    return {
        "title": "Mapping indisponible",
        "cause": exc.message,
        "action": action,
        "code": exc.code,
    }


def _readiness_payload(checks: list[ReadinessCheck]) -> dict[str, object]:
    ready = all(check.ok for check in checks)
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "code": "SIRCOM_READY" if ready else "SIRCOM_NOT_READY",
        "checks": [check.to_dict() for check in checks],
    }


def _check_data_dir(settings: Settings) -> ReadinessCheck:
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        if not settings.data_dir.is_dir():
            return ReadinessCheck("data_dir", False, "SIRCOM_DATA_DIR_NOT_DIRECTORY")
        probe = settings.data_dir / ".sircom-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        return ReadinessCheck("data_dir", False, "SIRCOM_DATA_DIR_NOT_WRITABLE")
    return ReadinessCheck("data_dir", True, "SIRCOM_DATA_DIR_OK")


def _check_sqlite(settings: Settings) -> ReadinessCheck:
    connection = None
    try:
        connection = connect_sqlite(
            settings.sqlite_path,
            busy_timeout_ms=settings.sqlite_busy_timeout_ms,
        )
        connection.execute("SELECT 1")
    except Exception:
        return ReadinessCheck("sqlite", False, "SIRCOM_SQLITE_UNAVAILABLE")
    finally:
        if connection is not None:
            connection.close()
    return ReadinessCheck("sqlite", True, "SIRCOM_SQLITE_OK")


def _check_disk(settings: Settings) -> ReadinessCheck:
    try:
        usage = shutil.disk_usage(settings.data_dir)
    except OSError:
        return ReadinessCheck("disk", False, "SIRCOM_DISK_UNAVAILABLE")

    free_mb = usage.free // (1024 * 1024)
    details = {"free_mb": free_mb, "required_mb": settings.disk_free_min_mb}
    if free_mb < settings.disk_free_min_mb:
        return ReadinessCheck("disk", False, "SIRCOM_DISK_FREE_LOW", details)
    return ReadinessCheck("disk", True, "SIRCOM_DISK_OK", details)


app = create_app()
