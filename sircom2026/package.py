from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError, sha256_file
from sircom2026.config import Settings
from sircom2026.csv_preview import (
    CSV_FINAL_ARTIFACT_ROLE,
    CSV_PREVIEW_STEP_KEY,
)
from sircom2026.image_matching import (
    EXPORT_IMAGES_FOLDER,
    MATCHING_ARTIFACT_ROLE,
    MATCHING_IMAGES_STEP_KEY,
    PROCESSED_IMAGES_ARTIFACT_ROLE,
)
from sircom2026.invalidation import fingerprint_payload, step_input_fingerprint
from sircom2026.lots import get_lot_detail
from sircom2026.mapping import MAPPING_STEP_KEY
from sircom2026.reports import (
    BUSINESS_REPORT_ARTIFACT_ROLE,
    REPORTS_STEP_KEY,
    TECHNICAL_REPORT_ARTIFACT_ROLE,
)
from sircom2026.state import record_problem
from sircom2026.worker import JobResult, WorkerJobContext, WorkerLeaseLost, enqueue_job


PACKAGE_STEP_KEY = "package_final"
PACKAGE_ARTIFACT_KIND = "zip"
PACKAGE_ARTIFACT_ROLE = "package-final"
PACKAGE_ARTIFACT_MIME_TYPE = "application/zip"
PACKAGE_RULES_VERSION = "package-final-v1"
PACKAGE_SCHEMA_VERSION = 1
PACKAGE_FILENAME_PREFIX = "sircom-2026-lot"
READY_STATUSES = ("termine", "termine_avec_alertes")

CSV_PACKAGE_NAME = "sircom-indesign-utf16.csv"
BUSINESS_REPORT_PACKAGE_NAME = "rapport-metier.md"
TECHNICAL_REPORT_PACKAGE_NAME = "rapport-technique.json"
MAPPING_PACKAGE_NAME = "mapping-utilise.json"
MANIFEST_PACKAGE_NAME = "manifest.json"


@dataclass(frozen=True)
class PackageGenerationResult:
    job: dict[str, Any]
    job_created: bool
    lot: dict[str, Any]


@dataclass(frozen=True)
class PersistedPackage:
    artifact: dict[str, Any]


class PackageError(ValueError):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


class PackageNotReady(RuntimeError):
    """Raised when the current final package cannot be exposed yet."""


class PackagePrerequisiteMissing(RuntimeError):
    def __init__(self, step_key: str, role: str) -> None:
        super().__init__(f"{step_key}:{role}")
        self.step_key = step_key
        self.role = role


def request_package_generation(
    repositories,
    *,
    settings: Settings,
    lot_id: str,
    idempotency_key: str,
    accept_warnings: bool = False,
) -> PackageGenerationResult:
    repositories.lots.get_required(lot_id)
    _require_no_blocking_problem(repositories, lot_id=lot_id)
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    try:
        sources = _build_package_sources(repositories, store, settings=settings, lot_id=lot_id)
    except PackagePrerequisiteMissing as exc:
        raise PackageError(
            409,
            "SIRCOM_PACKAGE_PREREQUISITE_MISSING",
            "Le package final n'a pas encore tous ses artefacts requis.",
            details={
                "step_key": exc.step_key,
                "role": exc.role,
            },
        ) from exc
    if sources["has_image_warnings"] and not accept_warnings:
        raise PackageError(
            409,
            "SIRCOM_PACKAGE_WARNINGS_DECISION_REQUIRED",
            "La génération du package nécessite une confirmation explicite des alertes ouvertes.",
            details={"step_key": MATCHING_IMAGES_STEP_KEY},
        )

    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=PACKAGE_STEP_KEY,
        input_payload={
            "accept_warnings": accept_warnings,
            "rules_version": PACKAGE_RULES_VERSION,
            "schema_version": PACKAGE_SCHEMA_VERSION,
        },
    )
    enqueued = enqueue_job(
        repositories,
        lot_id=lot_id,
        step_key=PACKAGE_STEP_KEY,
        idempotency_key=idempotency_key,
        input_fingerprint=input_fingerprint,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=PACKAGE_STEP_KEY,
        run_id=enqueued.job["run_id"],
        event_type="package.requested",
        payload={
            "has_image_warnings": sources["has_image_warnings"],
            "status": enqueued.job["status"],
            "step_key": PACKAGE_STEP_KEY,
        },
    )
    return PackageGenerationResult(
        job=enqueued.job,
        job_created=enqueued.created,
        lot=get_lot_detail(repositories, lot_id),
    )


def run_package_job(context: WorkerJobContext, *, settings: Settings) -> JobResult:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    context.set_progress(1, 5)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        if repositories.problems.count_open_by_severity(
            lot_id=context.lot_id,
            severity="bloquant",
        ):
            _record_blocking_problem(repositories, context)
            return JobResult(final_step_status="bloque")
        try:
            sources = _build_package_sources(
                repositories,
                store,
                settings=settings,
                lot_id=context.lot_id,
            )
        except PackagePrerequisiteMissing as exc:
            _record_missing_prerequisite_problem(repositories, context, exc)
            return JobResult(final_step_status="bloque")
        except PackageError as exc:
            _record_package_error_problem(repositories, context, exc)
            return JobResult(final_step_status="bloque")

    context.set_progress(2, 5)
    try:
        temp_package = _build_package_zip(
            settings=settings,
            lot_id=context.lot_id,
            sources=sources,
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        with context.database.transaction() as repositories:
            _record_build_problem(repositories, context, exc.__class__.__name__)
        return JobResult(final_step_status="bloque")

    context.set_progress(3, 5)
    try:
        package_sha256 = sha256_file(temp_package)
        package_size = temp_package.stat().st_size
        prepared = store.prepare_file_for_commit(
            lot_id=context.lot_id,
            filename=package_filename(context.lot_id),
            source_path=temp_package,
            sha256=package_sha256,
            size_bytes=package_size,
            mime_type=PACKAGE_ARTIFACT_MIME_TYPE,
        )

        context.set_progress(4, 5)
        with context.database.transaction() as repositories:
            _require_current_lease(repositories, context)
            repositories.problems.mark_open_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(PACKAGE_STEP_KEY,),
            )
            repositories.artifacts.mark_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(PACKAGE_STEP_KEY,),
            )
            artifact = store.create_committed_from_prepared_file(
                repositories,
                lot_id=context.lot_id,
                step_key=PACKAGE_STEP_KEY,
                run_id=context.run_id,
                kind=PACKAGE_ARTIFACT_KIND,
                role=PACKAGE_ARTIFACT_ROLE,
                prepared_file=prepared,
                metadata={
                    "download_filename": package_filename(context.lot_id),
                    "entries_count": len(sources["manifest_entries"]) + 1,
                    "has_image_warnings": sources["has_image_warnings"],
                    "rules_version": PACKAGE_RULES_VERSION,
                    "schema_version": PACKAGE_SCHEMA_VERSION,
                    "source_artifacts": _source_artifact_manifest(sources),
                },
                lease_version=context.leased_job.lease_version,
            )
            output_fingerprint = fingerprint_payload(
                {
                    "artifact_id": artifact["id"],
                    "artifact_sha256": artifact["sha256"],
                    "kind": "package_final",
                    "rules_version": PACKAGE_RULES_VERSION,
                    "schema_version": PACKAGE_SCHEMA_VERSION,
                    "source_artifacts": _source_artifact_manifest(sources),
                }
            )
            repositories.events.create(
                lot_id=context.lot_id,
                step_key=PACKAGE_STEP_KEY,
                run_id=context.run_id,
                event_type="package.generated",
                payload={
                    "artifact_id": artifact["id"],
                    "artifacts_count": len(sources["manifest_entries"]) + 1,
                    "size_bytes": artifact["size_bytes"],
                    "status": "termine_avec_alertes"
                    if sources["has_image_warnings"]
                    else "termine",
                    "step_key": PACKAGE_STEP_KEY,
                },
            )
    except Exception:
        temp_package.unlink(missing_ok=True)
        raise

    context.set_progress(5, 5)
    return JobResult(
        with_warnings=bool(sources["has_image_warnings"]),
        output_fingerprint=output_fingerprint,
    )


def get_persisted_package(
    repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PersistedPackage:
    repositories.lots.get_required(lot_id)
    step = repositories.steps.get_by_lot_key(lot_id, PACKAGE_STEP_KEY)
    if (
        step is None
        or not step["current_run_id"]
        or step["status"] not in READY_STATUSES
    ):
        raise PackageNotReady("Package is not ready.")
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=PACKAGE_STEP_KEY,
        run_id=step["current_run_id"],
        role=PACKAGE_ARTIFACT_ROLE,
    )
    if artifact is None or artifact["status"] != "committed":
        raise PackageNotReady("Package artifact is unavailable.")
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    try:
        store.open_for_read(repositories, lot_id=lot_id, artifact_id=artifact["id"])
    except (ArtifactUnavailableError, KeyError, ValueError) as exc:
        raise PackageNotReady("Package artifact is unavailable.") from exc
    return PersistedPackage(artifact=artifact)


def package_filename(lot_id: str) -> str:
    return f"{PACKAGE_FILENAME_PREFIX}-{lot_id}.zip"


def _build_package_sources(
    repositories,
    store: ArtifactStore,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any]:
    csv_final = _required_readable_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        role=CSV_FINAL_ARTIFACT_ROLE,
    )
    mapping = _required_readable_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        role="validated",
    )
    matching = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        role=MATCHING_ARTIFACT_ROLE,
    )
    processed_images = _required_readable_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        role=PROCESSED_IMAGES_ARTIFACT_ROLE,
    )
    business_report = _required_readable_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=REPORTS_STEP_KEY,
        role=BUSINESS_REPORT_ARTIFACT_ROLE,
    )
    technical_report = _required_readable_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=REPORTS_STEP_KEY,
        role=TECHNICAL_REPORT_ARTIFACT_ROLE,
    )
    _require_csv_path_root(csv_final.path.read_bytes(), settings.indesign_image_root)
    has_image_warnings = bool(
        matching.payload.get("has_warnings")
        or any(
            int(matching.payload.get(key) or 0) > 0
            for key in (
                "missing_count",
                "ambiguous_count",
                "unreferenced_count",
                "conversion_failed_count",
                "fallback_count",
                "tolerant_count",
            )
        )
    )
    return {
        "csv_final": csv_final,
        "mapping": mapping,
        "matching": matching,
        "processed_images": processed_images,
        "business_report": business_report,
        "technical_report": technical_report,
        "has_image_warnings": has_image_warnings,
        "manifest_entries": [],
    }


def _build_package_zip(
    *,
    settings: Settings,
    lot_id: str,
    sources: dict[str, Any],
) -> Path:
    temp_dir = settings.data_dir / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=f"{lot_id}-package-",
        suffix=".zip",
        dir=temp_dir,
        delete=False,
    )
    temp_path = Path(handle.name)
    handle.close()

    try:
        entries: list[dict[str, Any]] = []
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as package:
            _write_file_entry(
                package,
                entries,
                package_path=CSV_PACKAGE_NAME,
                role=CSV_FINAL_ARTIFACT_ROLE,
                source=sources["csv_final"],
            )
            _write_file_entry(
                package,
                entries,
                package_path=BUSINESS_REPORT_PACKAGE_NAME,
                role=BUSINESS_REPORT_ARTIFACT_ROLE,
                source=sources["business_report"],
            )
            _write_file_entry(
                package,
                entries,
                package_path=TECHNICAL_REPORT_PACKAGE_NAME,
                role=TECHNICAL_REPORT_ARTIFACT_ROLE,
                source=sources["technical_report"],
            )
            _write_file_entry(
                package,
                entries,
                package_path=MAPPING_PACKAGE_NAME,
                role="mapping-utilise",
                source=sources["mapping"],
            )
            _write_directory(package, f"{EXPORT_IMAGES_FOLDER}/")
            _copy_processed_images(package, entries, source=sources["processed_images"])
            manifest = _manifest_payload(
                lot_id=lot_id,
                entries=entries,
                sources=sources,
            )
            manifest_content = json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ).encode("utf-8")
            package.writestr(_zip_info(MANIFEST_PACKAGE_NAME), manifest_content)
        sources["manifest_entries"] = entries
        return temp_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _write_file_entry(
    package: zipfile.ZipFile,
    entries: list[dict[str, Any]],
    *,
    package_path: str,
    role: str,
    source,
) -> None:
    content = source.path.read_bytes()
    package.writestr(_zip_info(package_path), content)
    entries.append(
        {
            "path": package_path,
            "role": role,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "source_artifact_id": source.artifact["id"],
            "source_artifact_role": source.artifact["role"],
            "source_artifact_sha256": source.artifact["sha256"],
        }
    )


def _write_directory(package: zipfile.ZipFile, package_path: str) -> None:
    info = _zip_info(package_path)
    info.external_attr = 0o40755 << 16
    package.writestr(info, b"")


def _copy_processed_images(
    package: zipfile.ZipFile,
    entries: list[dict[str, Any]],
    *,
    source,
) -> None:
    with zipfile.ZipFile(source.path) as processed_images:
        for name in sorted(processed_images.namelist()):
            if name == f"{EXPORT_IMAGES_FOLDER}/":
                continue
            _require_package_image_path(name)
            content = processed_images.read(name)
            package.writestr(_zip_info(name), content)
            entries.append(
                {
                    "path": name,
                    "role": PROCESSED_IMAGES_ARTIFACT_ROLE,
                    "size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "source_artifact_id": source.artifact["id"],
                    "source_artifact_role": source.artifact["role"],
                    "source_artifact_sha256": source.artifact["sha256"],
                }
            )


def _manifest_payload(
    *,
    lot_id: str,
    entries: list[dict[str, Any]],
    sources: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "rules_version": PACKAGE_RULES_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "lot_id": lot_id,
        "package_filename": package_filename(lot_id),
        "directories": [
            {
                "path": f"{EXPORT_IMAGES_FOLDER}/",
                "role": "processed_images_directory",
            }
        ],
        "entries": entries,
        "source_artifacts": _source_artifact_manifest(sources),
        "notes": {
            "manifest_self_hash": "excluded",
            "package_root_files": [
                CSV_PACKAGE_NAME,
                BUSINESS_REPORT_PACKAGE_NAME,
                TECHNICAL_REPORT_PACKAGE_NAME,
                MAPPING_PACKAGE_NAME,
                MANIFEST_PACKAGE_NAME,
            ],
        },
    }


def _source_artifact_manifest(sources: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for source_key in (
        "csv_final",
        "mapping",
        "matching",
        "processed_images",
        "business_report",
        "technical_report",
    ):
        source = sources[source_key]
        result.append(
            {
                "key": source_key,
                "artifact_id": source.artifact["id"],
                "role": source.artifact["role"],
                "sha256": source.artifact["sha256"],
                "size_bytes": source.artifact["size_bytes"],
            }
        )
    return result


def _required_json_artifact(
    repositories,
    store: ArtifactStore,
    *,
    lot_id: str,
    step_key: str,
    role: str,
):
    readable = _required_readable_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=step_key,
        role=role,
    )
    try:
        payload = json.loads(readable.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackagePrerequisiteMissing(step_key, role) from exc
    if not isinstance(payload, dict):
        raise PackagePrerequisiteMissing(step_key, role)
    return _ReadableJsonArtifact(readable.artifact, readable.path, payload)


def _required_readable_artifact(
    repositories,
    store: ArtifactStore,
    *,
    lot_id: str,
    step_key: str,
    role: str,
):
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if step is None or not step["current_run_id"] or step["status"] not in READY_STATUSES:
        raise PackagePrerequisiteMissing(step_key, role)
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=step_key,
        run_id=step["current_run_id"],
        role=role,
    )
    if artifact is None or artifact["status"] != "committed":
        raise PackagePrerequisiteMissing(step_key, role)
    try:
        return store.open_for_read(
            repositories,
            lot_id=lot_id,
            artifact_id=artifact["id"],
        )
    except (ArtifactUnavailableError, KeyError, ValueError) as exc:
        raise PackagePrerequisiteMissing(step_key, role) from exc


@dataclass(frozen=True)
class _ReadableJsonArtifact:
    artifact: dict[str, Any]
    path: Path
    payload: dict[str, Any]


def _require_no_blocking_problem(repositories, *, lot_id: str) -> None:
    if repositories.problems.count_open_by_severity(lot_id=lot_id, severity="bloquant"):
        raise PackageError(
            409,
            "SIRCOM_PACKAGE_BLOCKERS_OPEN",
            "Le package final est bloqué par des problèmes ouverts.",
        )


def _require_csv_path_root(csv_content: bytes, indesign_image_root: str) -> None:
    expected_root = indesign_image_root.rstrip("/")
    text = csv_content.decode("utf-16")
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None or "@pathimg" not in reader.fieldnames:
        raise PackagePrerequisiteMissing(CSV_PREVIEW_STEP_KEY, CSV_FINAL_ARTIFACT_ROLE)
    for row in reader:
        value = str(row.get("@pathimg") or "").strip()
        if value and not value.startswith(f"{expected_root}/"):
            raise PackageError(
                409,
                "SIRCOM_PACKAGE_PATHIMG_ROOT_INVALID",
                "Les chemins @pathimg du CSV final ne visent pas la racine InDesign configurée.",
            )


def _require_package_image_path(path: str) -> None:
    if path.startswith("/") or "\\" in path:
        raise ValueError("Invalid package image path.")
    if ".." in Path(path).parts:
        raise ValueError("Invalid package image path.")
    if not path.startswith(f"{EXPORT_IMAGES_FOLDER}/"):
        raise ValueError("Invalid package image path.")
    relative = path.removeprefix(f"{EXPORT_IMAGES_FOLDER}/")
    if not relative or "/" in relative:
        raise ValueError("Invalid package image path.")


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path)
    info.date_time = (2026, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _require_current_lease(repositories, context: WorkerJobContext) -> None:
    if repositories.jobs.get_committable_by_run(
        lot_id=context.lot_id,
        step_key=context.step_key,
        run_id=context.run_id,
        lease_version=context.leased_job.lease_version,
        expected_input_fingerprint=context.leased_job.input_fingerprint,
    ) is None:
        raise WorkerLeaseLost("Worker lease is no longer current.")


def _record_blocking_problem(repositories, context: WorkerJobContext) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(PACKAGE_STEP_KEY,),
    )
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=PACKAGE_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_PACKAGE_BLOCKERS_OPEN",
        title="Package impossible",
        cause="Des problèmes bloquants restent ouverts sur le lot.",
        action="Corriger les problèmes bloquants puis redemander le package.",
    )


def _record_package_error_problem(
    repositories,
    context: WorkerJobContext,
    error: PackageError,
) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(PACKAGE_STEP_KEY,),
    )
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=PACKAGE_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code=error.code,
        title="Package impossible",
        cause=error.message,
        action="Corriger la configuration ou les artefacts courants puis redemander le package.",
        technical=error.details,
    )


def _record_missing_prerequisite_problem(
    repositories,
    context: WorkerJobContext,
    missing: PackagePrerequisiteMissing,
) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(PACKAGE_STEP_KEY,),
    )
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=PACKAGE_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_PACKAGE_PREREQUISITE_MISSING",
        title="Package impossible",
        cause="Un artefact courant requis pour générer le package est absent ou illisible.",
        action="Relancer l'étape indiquée puis redemander le package.",
        technical={
            "step_key": missing.step_key,
            "status": "missing",
        },
    )


def _record_build_problem(
    repositories,
    context: WorkerJobContext,
    error_code: str,
) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(PACKAGE_STEP_KEY,),
    )
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=PACKAGE_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_PACKAGE_BUILD_FAILED",
        title="Package impossible",
        cause="Le zip final n'a pas pu être assemblé.",
        action="Vérifier les artefacts courants puis redemander le package.",
        technical={"error_code": error_code},
    )
