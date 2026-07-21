from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from typing import Any

from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError
from sircom2026.config import Settings
from sircom2026.database import Repositories
from sircom2026.invalidation import fingerprint_payload
from sircom2026.state import record_problem
from sircom2026.transform import NORMALIZATION_ARTIFACT_ROLE, NORMALIZATION_STEP_KEY
from sircom2026.worker import JobResult, WorkerJobContext, WorkerLeaseLost


CSV_CONTRACT_STEP_KEY = "verification_csv_indesign"
CSV_CONTRACT_ARTIFACT_KIND = "json"
CSV_CONTRACT_ARTIFACT_ROLE = "result"
CSV_CONTRACT_MIME_TYPE = "application/json"
CSV_CONTRACT_RULES_VERSION = "csv-indesign-contract-v1"
CSV_CONTRACT_SCHEMA_VERSION = 1
UTF16_LE_BOM = b"\xff\xfe"
REQUIRED_2026_HEADERS = ("id_dossier", "imageid", "@pathimg")
FORBIDDEN_EMPTY_PLACEHOLDERS = {"#N/A", "N/C"}


@dataclass(frozen=True)
class CsvContractIssue:
    code: str
    title: str
    details: dict[str, Any]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "severity": "bloquant",
            "code": self.code,
            "title": self.title,
            "details": self.details,
        }


@dataclass(frozen=True)
class CsvContractReport:
    valid: bool
    headers: list[str]
    rows_count: int
    format_signature: dict[str, Any]
    issues: tuple[CsvContractIssue, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "headers": self.headers,
            "headers_count": len(self.headers),
            "rows_count": self.rows_count,
            "format_signature": self.format_signature,
            "issues": [issue.to_public_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class CurrentJsonArtifact:
    artifact: dict[str, Any]
    payload: dict[str, Any]


def write_indesign_csv_bytes(
    headers: list[str],
    rows: list[list[Any]],
) -> bytes:
    text_buffer = io.StringIO(newline="")
    writer = csv.writer(
        text_buffer,
        delimiter=",",
        quotechar='"',
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow([_csv_cell(header) for header in headers])
    for row in rows:
        writer.writerow([_csv_cell(value) for value in row])
    return UTF16_LE_BOM + text_buffer.getvalue().encode("utf-16-le")


def verify_indesign_csv_bytes(
    content: bytes,
    *,
    expected_headers: list[str] | None = None,
    required_headers: tuple[str, ...] = REQUIRED_2026_HEADERS,
) -> CsvContractReport:
    inspection = _inspect_csv_bytes(content)
    issues = list(inspection["issues"])
    headers = list(inspection["headers"])
    rows = list(inspection["rows"])

    if expected_headers is not None and headers != expected_headers:
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_HEADERS_ORDER_INVALID",
                "En-têtes CSV dans un ordre inattendu",
                {
                    "expected_count": len(expected_headers),
                    "actual_count": len(headers),
                },
            )
        )

    duplicates = sorted({header for header in headers if headers.count(header) > 1})
    if duplicates:
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_HEADERS_NOT_UNIQUE",
                "En-têtes CSV non uniques",
                {"headers": duplicates},
            )
        )

    if required_headers:
        expected_prefix = list(required_headers)
        if headers[: len(expected_prefix)] != expected_prefix:
            issues.append(
                CsvContractIssue(
                    "SIRCOM_CSV_REQUIRED_HEADERS_INVALID",
                    "Colonnes métier obligatoires mal positionnées",
                    {
                        "expected_prefix": expected_prefix,
                        "actual_prefix": headers[: len(expected_prefix)],
                    },
                )
            )

    for row_index, row in enumerate(rows, start=2):
        if len(row) != len(headers):
            issues.append(
                CsvContractIssue(
                    "SIRCOM_CSV_ROW_WIDTH_MISMATCH",
                    "Nombre de cellules incohérent",
                    {
                        "row_number": row_index,
                        "expected_cells": len(headers),
                        "actual_cells": len(row),
                    },
                )
            )
        for column_index, value in enumerate(row, start=1):
            if str(value).strip().upper() in FORBIDDEN_EMPTY_PLACEHOLDERS:
                issues.append(
                    CsvContractIssue(
                        "SIRCOM_CSV_FORBIDDEN_VALUE",
                        "Valeur de substitution interdite",
                        {
                            "row_number": row_index,
                            "column_index": column_index,
                        },
                    )
                )

    return CsvContractReport(
        valid=not issues,
        headers=headers,
        rows_count=len(rows),
        format_signature=inspection["format_signature"],
        issues=tuple(issues),
    )


def compare_csv_format_to_reference(
    reference_content: bytes,
    candidate_content: bytes,
) -> dict[str, Any]:
    reference = _inspect_csv_bytes(reference_content)
    candidate = _inspect_csv_bytes(candidate_content)
    compared_fields = ("encoding", "bom", "line_ending", "delimiter")
    matches = {
        field: (
            reference["format_signature"].get(field)
            == candidate["format_signature"].get(field)
        )
        for field in compared_fields
    }
    return {
        "format_matches": all(matches.values()) and not candidate["issues"],
        "matches": matches,
        "header_list_compared_as_normative": False,
        "reference": _public_signature(reference["format_signature"]),
        "candidate": _public_signature(candidate["format_signature"]),
    }


def build_csv_contract_candidate(
    normalized_payload: dict[str, Any],
) -> tuple[list[str], list[list[str]], bytes]:
    headers = [
        str(column["csv_name"])
        for column in normalized_payload.get("columns", [])
        if isinstance(column, dict) and column.get("csv_name") is not None
    ]
    rows: list[list[str]] = []
    for row in normalized_payload.get("rows", []):
        values = (
            row.get("values")
            if isinstance(row, dict) and isinstance(row.get("values"), dict)
            else {}
        )
        rows.append([_csv_cell(values.get(header, "")) for header in headers])
    return headers, rows, write_indesign_csv_bytes(headers, rows)


def run_csv_contract_verification_job(
    context: WorkerJobContext,
    *,
    settings: Settings,
) -> JobResult:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )

    context.set_progress(1, 4)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        normalized = _current_json_artifact(
            repositories,
            store,
            lot_id=context.lot_id,
            step_key=NORMALIZATION_STEP_KEY,
            role=NORMALIZATION_ARTIFACT_ROLE,
            ready_statuses=("termine", "termine_avec_alertes"),
        )
        if normalized is None:
            _record_missing_normalization_problem(repositories, context)
            return JobResult(final_step_status="bloque")

    context.set_progress(2, 4)
    headers, rows, candidate = build_csv_contract_candidate(normalized.payload)
    report = verify_indesign_csv_bytes(candidate, expected_headers=headers)
    public_report = report.to_public_dict()
    public_report.update(
        {
            "schema_version": CSV_CONTRACT_SCHEMA_VERSION,
            "rules_version": CSV_CONTRACT_RULES_VERSION,
            "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
            "candidate_size_bytes": len(candidate),
            "source_normalization_artifact_id": normalized.artifact["id"],
        }
    )
    report_content = json.dumps(
        public_report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    context.set_progress(3, 4)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        repositories.problems.mark_open_obsolete_for_steps(
            lot_id=context.lot_id,
            step_keys=(CSV_CONTRACT_STEP_KEY,),
        )
        repositories.artifacts.mark_obsolete_for_steps(
            lot_id=context.lot_id,
            step_keys=(CSV_CONTRACT_STEP_KEY,),
        )
        artifact = store.put_temp_then_commit(
            repositories,
            lot_id=context.lot_id,
            step_key=CSV_CONTRACT_STEP_KEY,
            run_id=context.run_id,
            kind=CSV_CONTRACT_ARTIFACT_KIND,
            role=CSV_CONTRACT_ARTIFACT_ROLE,
            filename="verification-contrat-csv-indesign.json",
            content=report_content,
            metadata={
                "candidate_size_bytes": len(candidate),
                "columns_count": len(headers),
                "issues_count": len(report.issues),
                "rows_count": len(rows),
                "rules_version": CSV_CONTRACT_RULES_VERSION,
                "schema_version": CSV_CONTRACT_SCHEMA_VERSION,
                "source_normalization_artifact_id": normalized.artifact["id"],
                "valid": report.valid,
            },
            mime_type=CSV_CONTRACT_MIME_TYPE,
            lease_version=context.leased_job.lease_version,
        )
        for issue in report.issues:
            record_problem(
                repositories,
                lot_id=context.lot_id,
                step_key=CSV_CONTRACT_STEP_KEY,
                run_id=context.run_id,
                severity="bloquant",
                code=issue.code,
                title=issue.title,
                cause="Le CSV candidat ne respecte pas le contrat InDesign.",
                action="Corriger la normalisation ou le mapping avant de générer l'aperçu CSV.",
                technical=issue.details,
            )
        output_fingerprint = fingerprint_payload(
            {
                "artifact_sha256": artifact["sha256"],
                "csv_contract_artifact_id": artifact["id"],
                "kind": "csv_contract_verification",
                "rules_version": CSV_CONTRACT_RULES_VERSION,
                "schema_version": CSV_CONTRACT_SCHEMA_VERSION,
                "source_normalization_artifact_id": normalized.artifact["id"],
                "valid": report.valid,
            }
        )
        repositories.events.create(
            lot_id=context.lot_id,
            step_key=CSV_CONTRACT_STEP_KEY,
            run_id=context.run_id,
            event_type="csv_contract.verified",
            payload={
                "artifact_id": artifact["id"],
                "columns_count": len(headers),
                "rows_count": len(rows),
                "status": "termine" if report.valid else "bloque",
                "step_key": CSV_CONTRACT_STEP_KEY,
            },
        )

    context.set_progress(4, 4)
    return JobResult(
        final_step_status=None if report.valid else "bloque",
        output_fingerprint=output_fingerprint,
    )


def _inspect_csv_bytes(content: bytes) -> dict[str, Any]:
    issues: list[CsvContractIssue] = []
    if not content.startswith(UTF16_LE_BOM):
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_UTF16_BOM_MISSING",
                "BOM UTF-16 LE manquant",
                {"expected_bom_hex": "fffe"},
            )
        )

    text = _decode_csv_text(content, issues)
    line_ending = _line_ending(text)
    if line_ending != "lf":
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_LINE_ENDING_NOT_LF",
                "Fins de ligne non LF",
                {"line_ending": line_ending},
            )
        )
    if text and not text.endswith("\n"):
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_FINAL_LF_MISSING",
                "Dernière ligne non terminée par LF",
                {},
            )
        )

    first_record = text.split("\n", 1)[0] if text else ""
    delimiter = "comma" if "," in first_record else "unknown"
    if delimiter != "comma":
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_SEPARATOR_NOT_COMMA",
                "Séparateur virgule non détecté",
                {"first_record_length": len(first_record)},
            )
        )

    headers: list[str] = []
    rows: list[list[str]] = []
    try:
        parsed = list(
            csv.reader(
                io.StringIO(text, newline=""),
                delimiter=",",
                quotechar='"',
                strict=True,
            )
        )
    except csv.Error as exc:
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_PARSE_ERROR",
                "CSV illisible",
                {"message": str(exc)},
            )
        )
        parsed = []

    if parsed:
        headers = [str(value) for value in parsed[0]]
        rows = [[str(value) for value in row] for row in parsed[1:]]
    else:
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_EMPTY",
                "CSV vide",
                {},
            )
        )

    signature = {
        "encoding": "utf-16-le-bom" if content.startswith(UTF16_LE_BOM) else "unknown",
        "bom": content[:2].hex() if len(content) >= 2 else "",
        "line_ending": line_ending,
        "delimiter": delimiter,
        "headers_count": len(headers),
        "rows_count": len(rows),
        "required_header_positions": {
            header: headers.index(header) if header in headers else None
            for header in REQUIRED_2026_HEADERS
        },
        "bytes_count": len(content),
    }
    return {
        "format_signature": signature,
        "headers": headers,
        "rows": rows,
        "issues": tuple(issues),
    }


def _decode_csv_text(content: bytes, issues: list[CsvContractIssue]) -> str:
    payload = content[2:] if content.startswith(UTF16_LE_BOM) else content
    try:
        return payload.decode("utf-16-le")
    except UnicodeDecodeError as exc:
        issues.append(
            CsvContractIssue(
                "SIRCOM_CSV_UTF16_DECODE_ERROR",
                "Décodage UTF-16 LE impossible",
                {"start": exc.start, "end": exc.end},
            )
        )
        return payload.decode("utf-16-le", errors="replace")


def _line_ending(text: str) -> str:
    has_crlf = "\r\n" in text
    without_crlf = text.replace("\r\n", "")
    has_lf = "\n" in without_crlf or has_crlf
    has_cr = "\r" in without_crlf
    if has_crlf and not has_cr and "\n" not in without_crlf:
        return "crlf"
    if has_crlf or (has_cr and has_lf):
        return "mixed"
    if has_cr:
        return "cr"
    if has_lf:
        return "lf"
    return "none"


def _public_signature(signature: dict[str, Any]) -> dict[str, Any]:
    return {
        "encoding": signature["encoding"],
        "bom": signature["bom"],
        "line_ending": signature["line_ending"],
        "delimiter": signature["delimiter"],
        "headers_count": signature["headers_count"],
        "rows_count": signature["rows_count"],
    }


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _current_json_artifact(
    repositories: Repositories,
    store: ArtifactStore,
    *,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> CurrentJsonArtifact | None:
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
    try:
        readable = store.open_for_read(
            repositories,
            lot_id=lot_id,
            artifact_id=artifact["id"],
        )
        payload = json.loads(readable.path.read_text(encoding="utf-8"))
    except (ArtifactUnavailableError, OSError, json.JSONDecodeError, KeyError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return CurrentJsonArtifact(artifact=artifact, payload=payload)


def _require_current_lease(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    if repositories.jobs.get_committable_by_run(
        lot_id=context.lot_id,
        step_key=context.step_key,
        run_id=context.run_id,
        lease_version=context.leased_job.lease_version,
        expected_input_fingerprint=context.leased_job.input_fingerprint,
    ) is None:
        raise WorkerLeaseLost("Worker lease is no longer current.")


def _record_missing_normalization_problem(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(CSV_CONTRACT_STEP_KEY,),
    )
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=CSV_CONTRACT_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_CSV_NORMALIZATION_NOT_READY",
        title="Normalisation indisponible",
        cause="Le vérificateur CSV ne trouve pas l'artefact de normalisation courant.",
        action="Relancer la fusion et la normalisation avant de vérifier le contrat CSV.",
    )
