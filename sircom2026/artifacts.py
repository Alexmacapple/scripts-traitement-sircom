from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sircom2026.database import Repositories


_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_SAFE_EXTENSION_RE = re.compile(r"^\.[A-Za-z0-9]{1,16}$")
_SAFE_PATH_PART_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_CURRENT_ARTIFACT_STATUS = "committed"


@dataclass(frozen=True)
class ReadableArtifact:
    artifact: dict[str, Any]
    path: Path
    filename: str
    media_type: str


@dataclass(frozen=True)
class ArtifactReconciliation:
    orphan_files: int = 0
    missing_files: int = 0
    hash_mismatches: int = 0
    expired_pending: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "orphan_files": self.orphan_files,
            "missing_files": self.missing_files,
            "hash_mismatches": self.hash_mismatches,
            "expired_pending": self.expired_pending,
        }


class ArtifactUnavailableError(RuntimeError):
    """Raised when an artifact must not be exposed as a current download."""


class ArtifactStore:
    def __init__(self, data_dir: Path, *, pending_ttl_seconds: int = 3600) -> None:
        self.root = data_dir
        self.pending_ttl_seconds = pending_ttl_seconds

    def put_temp_then_commit(
        self,
        repositories: Repositories,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        kind: str,
        role: str,
        filename: str,
        content: bytes,
        metadata: dict[str, Any] | None = None,
        artifact_id: str | None = None,
        mime_type: str | None = None,
        lease_version: int,
    ) -> dict[str, Any]:
        artifact = self.create_pending(
            repositories,
            lot_id=lot_id,
            step_key=step_key,
            run_id=run_id,
            kind=kind,
            role=role,
            filename=filename,
            content=content,
            metadata=metadata,
            artifact_id=artifact_id,
            mime_type=mime_type,
            lease_version=lease_version,
        )
        temp_path = self._temp_path(lot_id, artifact["id"])
        final_path = self.path_for(artifact["relative_path"])
        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temp_path, final_path)
        committed = repositories.artifacts.update_status(artifact["id"], _CURRENT_ARTIFACT_STATUS)
        repositories.lots.refresh_artifact_counters(lot_id)
        return committed

    def create_pending(
        self,
        repositories: Repositories,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        kind: str,
        role: str,
        filename: str,
        content: bytes,
        metadata: dict[str, Any] | None = None,
        artifact_id: str | None = None,
        mime_type: str | None = None,
        lease_version: int,
    ) -> dict[str, Any]:
        lot = repositories.lots.get_required(lot_id)
        if lot["status"] in {"supprime", "purge"}:
            raise ArtifactUnavailableError("Deleted lots cannot receive artifacts.")
        self._require_active_job(
            repositories,
            lot_id=lot_id,
            step_key=step_key,
            run_id=run_id,
            lease_version=lease_version,
        )
        row_id = artifact_id or _new_artifact_id()
        safe_lot_id = safe_path_part(lot_id, "lot_id")
        safe_row_id = safe_path_part(row_id, "artifact_id")
        internal_filename = internal_artifact_filename(safe_row_id, filename)
        temp_path = self._temp_path(lot_id, row_id)
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(content)
        sha256 = sha256_file(temp_path)
        size_bytes = temp_path.stat().st_size
        relative_path = f"lots/{safe_lot_id}/artifacts/{safe_row_id}/{internal_filename}"
        try:
            return repositories.artifacts.create(
                lot_id=lot_id,
                step_key=step_key,
                run_id=run_id,
                kind=kind,
                role=role,
                relative_path=relative_path,
                sha256=sha256,
                size_bytes=size_bytes,
                mime_type=mime_type or guess_media_type(internal_filename),
                metadata=metadata,
                status="pending",
                artifact_id=row_id,
            )
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def open_for_read(
        self,
        repositories: Repositories,
        *,
        lot_id: str,
        artifact_id: str,
    ) -> ReadableArtifact:
        lot = repositories.lots.get_required(lot_id)
        artifact = repositories.artifacts.get_for_lot(lot_id, artifact_id)
        if artifact is None:
            raise ArtifactUnavailableError("Artifact does not belong to the lot.")
        if lot["status"] in {"supprime", "purge"}:
            raise ArtifactUnavailableError("Deleted lots cannot expose downloads.")
        if artifact["status"] != _CURRENT_ARTIFACT_STATUS:
            raise ArtifactUnavailableError("Artifact is not current.")

        artifact_path = self.path_for(artifact["relative_path"])
        if not artifact_path.is_file():
            _mark_artifact_obsolete_with_problem(
                repositories,
                artifact,
                code="SIRCOM_ARTIFACT_FILE_MISSING",
                title="Fichier artefact manquant",
                cause="Un artefact reference en base n'existe plus dans le store local.",
                action="Relancer l'etape qui produit cet artefact avant de le telecharger.",
            )
            raise ArtifactUnavailableError("Artifact file is missing.")
        actual_sha256 = sha256_file(artifact_path)
        if actual_sha256 != artifact["sha256"]:
            _mark_artifact_obsolete_with_problem(
                repositories,
                artifact,
                code="SIRCOM_ARTIFACT_HASH_MISMATCH",
                title="Empreinte artefact incoherente",
                cause="Un artefact reference en base ne correspond plus a son empreinte SHA-256.",
                action="Relancer l'etape qui produit cet artefact pour recreer une version coherente.",
                technical={"actual_sha256": actual_sha256},
            )
            raise ArtifactUnavailableError("Artifact checksum mismatch.")

        return ReadableArtifact(
            artifact=artifact,
            path=artifact_path,
            filename=download_filename(artifact),
            media_type=artifact["mime_type"] or "application/octet-stream",
        )

    def reconcile(self, repositories: Repositories) -> ArtifactReconciliation:
        known_paths: set[str] = set()
        known_temp_paths: set[str] = set()
        missing_files = 0
        hash_mismatches = 0
        expired_pending = 0
        for artifact in repositories.artifacts.list_all():
            known_paths.add(artifact["relative_path"])
            path = self.path_for(artifact["relative_path"])
            if artifact["status"] == "committed":
                if not path.is_file():
                    _mark_artifact_obsolete_with_problem(
                        repositories,
                        artifact,
                        code="SIRCOM_ARTIFACT_FILE_MISSING",
                        title="Fichier artefact manquant",
                        cause="Un artefact reference en base n'existe plus dans le store local.",
                        action="Relancer l'etape qui produit cet artefact avant de le telecharger.",
                    )
                    missing_files += 1
                else:
                    actual_sha256 = sha256_file(path)
                    if actual_sha256 != artifact["sha256"]:
                        _mark_artifact_obsolete_with_problem(
                            repositories,
                            artifact,
                            code="SIRCOM_ARTIFACT_HASH_MISMATCH",
                            title="Empreinte artefact incoherente",
                            cause=(
                                "Un artefact reference en base ne correspond "
                                "plus a son empreinte SHA-256."
                            ),
                            action=(
                                "Relancer l'etape qui produit cet artefact "
                                "pour recreer une version coherente."
                            ),
                            technical={"actual_sha256": actual_sha256},
                        )
                        hash_mismatches += 1
            elif artifact["status"] == "pending":
                temp_path = self._temp_path(artifact["lot_id"], artifact["id"])
                known_temp_paths.add(self._relative_to_root(temp_path))
                if self._pending_is_expired(artifact):
                    new_status = "quarantined" if temp_path.exists() else "obsolete"
                    if temp_path.exists():
                        self._quarantine_file(temp_path, category="pending")
                    repositories.artifacts.update_status(artifact["id"], new_status)
                    expired_pending += 1

        orphan_files = self._quarantine_orphan_files(known_paths, known_temp_paths)
        return ArtifactReconciliation(
            orphan_files=orphan_files,
            missing_files=missing_files,
            hash_mismatches=hash_mismatches,
            expired_pending=expired_pending,
        )

    def _require_active_job(
        self,
        repositories: Repositories,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        lease_version: int,
    ) -> None:
        if repositories.jobs.get_committable_by_run(
            lot_id=lot_id,
            step_key=step_key,
            run_id=run_id,
            lease_version=lease_version,
        ) is not None:
            return
        repositories.events.create(
            lot_id=lot_id,
            step_key=step_key,
            run_id=run_id,
            level="warning",
            event_type="artifact.commit_rejected",
            payload={
                "code": "SIRCOM_ARTIFACT_COMMIT_REJECTED",
                "run_id": run_id,
                "step_key": step_key,
            },
        )
        raise ArtifactUnavailableError("Artifact run is not active.")

    def path_for(self, relative_path: str) -> Path:
        candidate = self.root / relative_path
        root = self.root.resolve(strict=False)
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise ValueError("Artifact path escapes the data directory.")
        return resolved

    def _temp_path(self, lot_id: str, artifact_id: str) -> Path:
        lot_part = safe_path_part(lot_id, "lot_id")
        artifact_part = safe_path_part(artifact_id, "artifact_id")
        return self.path_for(f"lots/{lot_part}/tmp/{artifact_part}.part")

    def _pending_is_expired(self, artifact: dict[str, Any]) -> bool:
        try:
            created_at = datetime.fromisoformat(artifact["created_at"])
        except (TypeError, ValueError):
            return True
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - created_at > timedelta(seconds=self.pending_ttl_seconds)

    def _quarantine_orphan_files(self, known_paths: set[str], known_temp_paths: set[str]) -> int:
        artifact_root = self.root / "lots"
        if not artifact_root.exists():
            return 0

        orphan_files = 0
        for path in artifact_root.glob("*/artifacts/**/*"):
            if not path.is_file():
                continue
            relative_path = self._relative_to_root(path)
            if relative_path in known_paths:
                continue
            orphan_files += 1
            self._quarantine_file(path, category="orphans")
        for path in artifact_root.glob("*/tmp/*.part"):
            if not path.is_file():
                continue
            relative_path = self._relative_to_root(path)
            if relative_path in known_temp_paths:
                continue
            orphan_files += 1
            self._quarantine_file(path, category="orphans")
        return orphan_files

    def _quarantine_file(self, path: Path, *, category: str) -> None:
        quarantine_path = (
            self.root
            / "quarantine"
            / category
            / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex}-{path.name}"
        )
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, quarantine_path)

    def _relative_to_root(self, path: Path) -> str:
        root = self.root.resolve(strict=False)
        return path.resolve(strict=False).relative_to(root).as_posix()


def safe_artifact_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name:
        return "artifact.bin"
    safe_name = _SAFE_FILENAME_RE.sub("-", name).strip(".-")
    return safe_name or "artifact.bin"


def safe_path_part(value: str, name: str) -> str:
    if not _SAFE_PATH_PART_RE.fullmatch(value):
        raise ValueError(f"{name} contains unsafe characters.")
    return value


def internal_artifact_filename(artifact_id: str, source_filename: str) -> str:
    extension = Path(source_filename).suffix.lower()
    if not _SAFE_EXTENSION_RE.fullmatch(extension):
        extension = ".bin"
    return f"{safe_path_part(artifact_id, 'artifact_id')}{extension}"


def download_filename(artifact: dict[str, Any]) -> str:
    extension = Path(artifact["relative_path"]).suffix
    base = safe_artifact_filename(f"{artifact['role'] or artifact['kind']}{extension}")
    return base


def guess_media_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _new_artifact_id() -> str:
    return f"artifact_{uuid.uuid4().hex}"


def _mark_artifact_obsolete_with_problem(
    repositories: Repositories,
    artifact: dict[str, Any],
    *,
    code: str,
    title: str,
    cause: str,
    action: str,
    technical: dict[str, Any] | None = None,
) -> None:
    repositories.artifacts.update_status(artifact["id"], "obsolete")
    repositories.lots.refresh_artifact_counters(artifact["lot_id"])
    repositories.problems.create(
        lot_id=artifact["lot_id"],
        step_key=artifact["step_key"],
        run_id=artifact["run_id"],
        severity="alerte",
        code=code,
        title=title,
        cause=cause,
        message=cause,
        action=action,
        location={"artifact_id": artifact["id"]},
        technical={
            "artifact_id": artifact["id"],
            "expected_sha256": artifact["sha256"],
            **(technical or {}),
        },
    )
