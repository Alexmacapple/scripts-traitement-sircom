from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sircom2026.artifacts import (
    ArtifactStore,
    ArtifactUnavailableError,
    cleanup_artifact_paths,
)
from sircom2026.config import Settings
from sircom2026.csv_contract import CSV_CONTRACT_ARTIFACT_ROLE, CSV_CONTRACT_STEP_KEY
from sircom2026.csv_preview import (
    CSV_FINAL_ARTIFACT_ROLE,
    CSV_PREVIEW_ARTIFACT_ROLE,
    CSV_PREVIEW_STEP_KEY,
)
from sircom2026.database import Repositories, TECHNICAL_EVENT_PAYLOAD_KEYS
from sircom2026.excel_diagnostic_pipeline import (
    DIAGNOSTIC_ARTIFACT_ROLE,
    DIAGNOSTIC_STEP_KEY,
)
from sircom2026.image_matching import (
    MATCHING_ARTIFACT_ROLE,
    MATCHING_IMAGES_STEP_KEY,
    PROCESSED_IMAGES_ARTIFACT_ROLE,
)
from sircom2026.images import (
    INSPECTION_ARTIFACT_ROLE,
    INSPECTION_IMAGES_STEP_KEY,
    UPLOAD_IMAGES_STEP_KEY,
)
from sircom2026.invalidation import fingerprint_payload
from sircom2026.mapping import MAPPING_STEP_KEY
from sircom2026.reports_rendering import (
    build_business_report as _render_business_report,
    build_technical_report as _render_technical_report,
)
from sircom2026.sorting import SORT_ARTIFACT_ROLE, SORT_STEP_KEY
from sircom2026.state import record_problem
from sircom2026.transform import (
    FUSION_ARTIFACT_ROLE,
    FUSION_STEP_KEY,
    NORMALIZATION_ARTIFACT_ROLE,
    NORMALIZATION_STEP_KEY,
)
from sircom2026.worker import JobResult, WorkerJobContext, WorkerLeaseLost


REPORTS_STEP_KEY = "rapports"
BUSINESS_REPORT_ARTIFACT_KIND = "markdown"
BUSINESS_REPORT_ARTIFACT_ROLE = "rapport-metier"
BUSINESS_REPORT_FILENAME = "rapport-metier.md"
BUSINESS_REPORT_MIME_TYPE = "text/markdown; charset=utf-8"
TECHNICAL_REPORT_ARTIFACT_KIND = "json"
TECHNICAL_REPORT_ARTIFACT_ROLE = "rapport-technique"
TECHNICAL_REPORT_FILENAME = "rapport-technique.json"
TECHNICAL_REPORT_MIME_TYPE = "application/json"
REPORTS_RULES_VERSION = "reports-v1"
REPORTS_SCHEMA_VERSION = 1
READY_STATUSES = ("termine", "termine_avec_alertes")


@dataclass(frozen=True)
class CurrentJsonArtifact:
    artifact: dict[str, Any]
    payload: dict[str, Any]


@dataclass(frozen=True)
class PersistedReports:
    business_artifact: dict[str, Any]
    technical_artifact: dict[str, Any]


class ReportsNotReady(RuntimeError):
    """Raised when current reports cannot be exposed yet."""


class ReportsPrerequisiteMissing(RuntimeError):
    def __init__(self, step_key: str, role: str) -> None:
        super().__init__(f"{step_key}:{role}")
        self.step_key = step_key
        self.role = role


def run_reports_job(context: WorkerJobContext, *, settings: Settings) -> JobResult:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )

    context.set_progress(1, 4)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        try:
            snapshot = _build_report_snapshot(
                repositories,
                store,
                lot_id=context.lot_id,
            )
        except ReportsPrerequisiteMissing as exc:
            _record_missing_prerequisite_problem(repositories, context, exc)
            return JobResult(final_step_status="bloque")

    context.set_progress(2, 4)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    business_content = build_business_report(
        snapshot, generated_at=generated_at
    ).encode("utf-8")
    technical_report = build_technical_report(snapshot, generated_at=generated_at)
    technical_content = json.dumps(
        technical_report,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ).encode("utf-8")

    context.set_progress(3, 4)
    committed_artifact_paths = []
    reports_committed = False
    try:
        with context.database.transaction() as repositories:
            _require_current_lease(repositories, context)
            repositories.problems.mark_open_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(REPORTS_STEP_KEY,),
            )
            repositories.artifacts.mark_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(REPORTS_STEP_KEY,),
            )
            source_metadata = _report_source_metadata(snapshot)
            business_artifact = store.put_temp_then_commit(
                repositories,
                lot_id=context.lot_id,
                step_key=REPORTS_STEP_KEY,
                run_id=context.run_id,
                kind=BUSINESS_REPORT_ARTIFACT_KIND,
                role=BUSINESS_REPORT_ARTIFACT_ROLE,
                filename=BUSINESS_REPORT_FILENAME,
                content=business_content,
                metadata=dict(source_metadata),
                mime_type=BUSINESS_REPORT_MIME_TYPE,
                lease_version=context.leased_job.lease_version,
            )
            committed_artifact_paths.append(
                store.path_for(business_artifact["relative_path"])
            )
            technical_artifact = store.put_temp_then_commit(
                repositories,
                lot_id=context.lot_id,
                step_key=REPORTS_STEP_KEY,
                run_id=context.run_id,
                kind=TECHNICAL_REPORT_ARTIFACT_KIND,
                role=TECHNICAL_REPORT_ARTIFACT_ROLE,
                filename=TECHNICAL_REPORT_FILENAME,
                content=technical_content,
                metadata=dict(source_metadata),
                mime_type=TECHNICAL_REPORT_MIME_TYPE,
                lease_version=context.leased_job.lease_version,
            )
            committed_artifact_paths.append(
                store.path_for(technical_artifact["relative_path"])
            )
            output_fingerprint = fingerprint_payload(
                {
                    "business_artifact_id": business_artifact["id"],
                    "business_sha256": business_artifact["sha256"],
                    "kind": "reports",
                    "rules_version": REPORTS_RULES_VERSION,
                    "schema_version": REPORTS_SCHEMA_VERSION,
                    "source_artifacts": {
                        key: {
                            "id": artifact["id"],
                            "sha256": artifact["sha256"],
                        }
                        for key, artifact in snapshot["artifacts"].items()
                        if artifact is not None
                    },
                    "technical_artifact_id": technical_artifact["id"],
                    "technical_sha256": technical_artifact["sha256"],
                }
            )
            has_alerts = snapshot["problem_counts"]["alerte"] > 0
            repositories.events.create(
                lot_id=context.lot_id,
                step_key=REPORTS_STEP_KEY,
                run_id=context.run_id,
                event_type="reports.generated",
                payload={
                    "artifact_id": business_artifact["id"],
                    "artifacts_count": 2,
                    "rows_count": snapshot["integrity"]["csv_rows_count"],
                    "status": "termine_avec_alertes" if has_alerts else "termine",
                    "step_key": REPORTS_STEP_KEY,
                },
            )
            reports_committed = True
    finally:
        if not reports_committed:
            cleanup_artifact_paths(committed_artifact_paths)

    context.set_progress(4, 4)
    return JobResult(
        with_warnings=has_alerts,
        output_fingerprint=output_fingerprint,
        require_next_validations=("package_final",),
    )


def get_persisted_reports(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PersistedReports:
    repositories.lots.get_required(lot_id)
    step = repositories.steps.get_by_lot_key(lot_id, REPORTS_STEP_KEY)
    if (
        step is None
        or not step["current_run_id"]
        or step["status"] not in READY_STATUSES
    ):
        raise ReportsNotReady("Reports are not ready.")

    business_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=REPORTS_STEP_KEY,
        run_id=step["current_run_id"],
        role=BUSINESS_REPORT_ARTIFACT_ROLE,
    )
    technical_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=REPORTS_STEP_KEY,
        run_id=step["current_run_id"],
        role=TECHNICAL_REPORT_ARTIFACT_ROLE,
    )
    if (
        business_artifact is None
        or technical_artifact is None
        or business_artifact["status"] != "committed"
        or technical_artifact["status"] != "committed"
    ):
        raise ReportsNotReady("Reports artifacts are unavailable.")

    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    try:
        store.open_for_read(
            repositories, lot_id=lot_id, artifact_id=business_artifact["id"]
        )
        store.open_for_read(
            repositories, lot_id=lot_id, artifact_id=technical_artifact["id"]
        )
    except (ArtifactUnavailableError, KeyError, ValueError) as exc:
        raise ReportsNotReady("Reports artifacts are unavailable.") from exc

    return PersistedReports(
        business_artifact=business_artifact,
        technical_artifact=technical_artifact,
    )


def build_business_report(snapshot: dict[str, Any], *, generated_at: str) -> str:
    return _render_business_report(snapshot, generated_at=generated_at)


def build_technical_report(
    snapshot: dict[str, Any], *, generated_at: str
) -> dict[str, Any]:
    return _render_technical_report(
        snapshot,
        generated_at=generated_at,
        schema_version=REPORTS_SCHEMA_VERSION,
        rules_version=REPORTS_RULES_VERSION,
        technical_event_payload_keys=TECHNICAL_EVENT_PAYLOAD_KEYS,
    )


def _build_report_snapshot(
    repositories: Repositories,
    store: ArtifactStore,
    *,
    lot_id: str,
) -> dict[str, Any]:
    lot = repositories.lots.get_required(lot_id)
    steps = repositories.steps.list_for_lot(lot_id)
    problems = repositories.problems.list_for_lot(lot_id, limit=500)
    problem_counts = {
        severity: repositories.problems.count_open_by_severity(
            lot_id=lot_id,
            severity=severity,
        )
        for severity in ("bloquant", "alerte", "information")
    }
    events = repositories.events.list_for_lot(lot_id, limit=200)

    excel_source = _required_current_artifact(
        repositories,
        lot_id=lot_id,
        step_key="upload_excel",
        role="source",
        ready_statuses=READY_STATUSES,
    )
    diagnostic = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=DIAGNOSTIC_STEP_KEY,
        role=DIAGNOSTIC_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    mapping = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        role="validated",
        ready_statuses=READY_STATUSES,
    )
    fusion = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=FUSION_STEP_KEY,
        role=FUSION_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    normalization = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=NORMALIZATION_STEP_KEY,
        role=NORMALIZATION_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    sort = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        role=SORT_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    csv_contract = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=CSV_CONTRACT_STEP_KEY,
        role=CSV_CONTRACT_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    csv_preview = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        role=CSV_PREVIEW_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    csv_final = _required_current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        role=CSV_FINAL_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    image_zip_source = _current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        role="source",
        ready_statuses=READY_STATUSES,
    )
    if image_zip_source is None:
        inspection_artifact = None
        inspection_payload = _empty_image_inspection_payload()
        matching_artifact = None
        matching_payload = _empty_image_matching_payload()
        processed_images = None
    else:
        inspection = _required_json_artifact(
            repositories,
            store,
            lot_id=lot_id,
            step_key=INSPECTION_IMAGES_STEP_KEY,
            role=INSPECTION_ARTIFACT_ROLE,
            ready_statuses=READY_STATUSES,
        )
        matching = _required_json_artifact(
            repositories,
            store,
            lot_id=lot_id,
            step_key=MATCHING_IMAGES_STEP_KEY,
            role=MATCHING_ARTIFACT_ROLE,
            ready_statuses=READY_STATUSES,
        )
        processed_images = _current_artifact(
            repositories,
            lot_id=lot_id,
            step_key=MATCHING_IMAGES_STEP_KEY,
            role=PROCESSED_IMAGES_ARTIFACT_ROLE,
            ready_statuses=READY_STATUSES,
        )
        inspection_artifact = inspection.artifact
        inspection_payload = inspection.payload
        matching_artifact = matching.artifact
        matching_payload = matching.payload
    artifacts = {
        "excel_source": excel_source,
        "diagnostic": diagnostic.artifact,
        "mapping": mapping.artifact,
        "fusion": fusion.artifact,
        "normalization": normalization.artifact,
        "sort": sort.artifact,
        "csv_contract": csv_contract.artifact,
        "csv_preview": csv_preview.artifact,
        "csv_final": csv_final,
        "image_zip_source": image_zip_source,
        "inspection": inspection_artifact,
        "matching": matching_artifact,
        "processed_images": processed_images,
    }
    return {
        "lot": lot,
        "steps": steps,
        "problems": problems,
        "problem_counts": problem_counts,
        "events": events,
        "artifacts": artifacts,
        "diagnostic": diagnostic.payload,
        "mapping": mapping.payload,
        "fusion": fusion.payload,
        "normalization": normalization.payload,
        "sort": sort.payload,
        "csv_contract": csv_contract.payload,
        "csv_preview": csv_preview.payload,
        "inspection": inspection_payload,
        "matching": matching_payload,
        "integrity": _integrity_payload(
            normalization.payload,
            csv_preview.payload,
            matching_payload,
            problems_count=sum(problem_counts.values()),
        ),
    }


def _report_source_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "rules_version": REPORTS_RULES_VERSION,
        "schema_version": REPORTS_SCHEMA_VERSION,
        "source_csv_artifact_id": snapshot["artifacts"]["csv_final"]["id"],
    }
    matching = snapshot["artifacts"].get("matching")
    if matching is not None:
        metadata["source_matching_artifact_id"] = matching["id"]
    return metadata


def _empty_image_inspection_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rules_version": "image-zip-inspection-v2",
        "inspectable": False,
        "image_count": 0,
        "images": [],
        "skipped": True,
        "reason": "no_image_zip",
    }


def _empty_image_matching_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rules_version": "image-matching-v1",
        "rows_count": 0,
        "bindings_count": 0,
        "bindings": [],
        "manual_resolutions": [],
        "matched_count": 0,
        "processed_images_count": 0,
        "missing_count": 0,
        "ambiguous_count": 0,
        "unreferenced_count": 0,
        "conversion_failed_count": 0,
        "fallback_count": 0,
        "tolerant_count": 0,
        "blocking": False,
        "has_warnings": False,
        "skipped": True,
        "reason": "no_image_zip",
    }


def _required_json_artifact(
    repositories: Repositories,
    store: ArtifactStore,
    *,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> CurrentJsonArtifact:
    artifact = _required_current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        role=role,
        ready_statuses=ready_statuses,
    )
    try:
        readable = store.open_for_read(
            repositories,
            lot_id=lot_id,
            artifact_id=artifact["id"],
        )
        payload = json.loads(readable.path.read_text(encoding="utf-8"))
    except (
        ArtifactUnavailableError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
    ) as exc:
        raise ReportsPrerequisiteMissing(step_key, role) from exc
    if not isinstance(payload, dict):
        raise ReportsPrerequisiteMissing(step_key, role)
    return CurrentJsonArtifact(artifact=artifact, payload=payload)


def _required_current_artifact(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> dict[str, Any]:
    artifact = _current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        role=role,
        ready_statuses=ready_statuses,
    )
    if artifact is None:
        raise ReportsPrerequisiteMissing(step_key, role)
    return artifact


def _current_artifact(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> dict[str, Any] | None:
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if (
        step is None
        or not step["current_run_id"]
        or step["status"] not in ready_statuses
    ):
        return None
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=step_key,
        run_id=step["current_run_id"],
        role=role,
    )
    if artifact is None or artifact["status"] != "committed":
        return None
    return artifact


def _record_missing_prerequisite_problem(
    repositories: Repositories,
    context: WorkerJobContext,
    missing: ReportsPrerequisiteMissing,
) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(REPORTS_STEP_KEY,),
    )
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=REPORTS_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_REPORTS_PREREQUISITE_MISSING",
        title="Rapports impossibles",
        cause="Un artefact courant requis pour générer les rapports est absent ou illisible.",
        action="Relancer l'étape indiquée puis relancer les rapports.",
        technical={
            "step_key": missing.step_key,
            "status": "missing",
        },
    )


def _require_current_lease(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    if (
        repositories.jobs.get_committable_by_run(
            lot_id=context.lot_id,
            step_key=context.step_key,
            run_id=context.run_id,
            lease_version=context.leased_job.lease_version,
            expected_input_fingerprint=context.leased_job.input_fingerprint,
        )
        is None
    ):
        raise WorkerLeaseLost("Worker lease is no longer current.")


def _integrity_payload(
    normalization: dict[str, Any],
    csv_preview: dict[str, Any],
    matching: dict[str, Any],
    *,
    problems_count: int,
) -> dict[str, int]:
    source_ids = {
        str(row.get("id_dossier") or "").strip()
        for row in normalization.get("rows", [])
        if isinstance(row, dict) and str(row.get("id_dossier") or "").strip()
    }
    removed_empty_columns_count = _int(
        normalization.get("removed_empty_columns_count")
    ) + _int(normalization.get("upstream_removed_empty_columns_count"))
    return {
        "source_ids_count": len(source_ids),
        "csv_rows_count": _int(csv_preview.get("rows_count")),
        "removed_rows_without_id_count": _int(
            csv_preview.get("removed_rows_without_id_count")
        ),
        "removed_empty_columns_count": removed_empty_columns_count,
        "present_images_count": _int(matching.get("processed_images_count")),
        "missing_images_count": _int(matching.get("missing_count")),
        "ignored_images_count": _int(matching.get("unreferenced_count")),
        "open_problems_count": problems_count,
    }


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
