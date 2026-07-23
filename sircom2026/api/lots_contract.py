from __future__ import annotations

from typing import Any

from fastapi import Request

from sircom2026.api.errors import ApiError
from sircom2026.csv_preview import CsvPreviewError
from sircom2026.database import LOT_WRITE_BLOCKED_STATUSES
from sircom2026.image_matching import ImageResolutionError
from sircom2026.mapping import MappingError
from sircom2026.package import PackageError
from sircom2026.sorting import SortDecisionError


PERSISTED_MAPPING_VALIDATION_ERROR_CODES = {
    "SIRCOM_MAPPING_CSV_HEADER_COLLISION",
    "SIRCOM_MAPPING_CSV_NAME_MISSING",
    "SIRCOM_MAPPING_ID_DOSSIER_INVALID",
    "SIRCOM_MAPPING_NO_BUSINESS_COLUMN",
}


def lot_not_found() -> ApiError:
    return ApiError(
        404,
        "SIRCOM_LOT_NOT_FOUND",
        "Lot introuvable.",
    )


def lot_not_mutable() -> ApiError:
    return ApiError(
        409,
        "SIRCOM_LOT_NOT_MUTABLE",
        "Lot non modifiable.",
    )


def require_mutable_upload_target(repositories: Any, lot_id: str) -> None:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise lot_not_mutable()


def mapping_submission_to_dict(payload: Any) -> dict[str, object]:
    return {
        "structural_fingerprint": payload.structural_fingerprint,
        "columns": [
            {
                "id": column.id,
                "status": column.status,
                "csv_name": column.csv_name,
                "logical_role": column.logical_role,
                "suppression_reason": column.suppression_reason,
            }
            for column in payload.columns
        ],
    }


def mapping_artifact_response(
    artifact: dict[str, object], lot_id: str
) -> dict[str, object]:
    return {
        "id": artifact["id"],
        "kind": artifact["kind"],
        "role": artifact["role"],
        "status": artifact["status"],
        "size_bytes": artifact["size_bytes"],
        "sha256": artifact["sha256"],
        "mime_type": artifact["mime_type"],
        "download_url": f"/api/lots/{lot_id}/downloads/{artifact['id']}",
    }


def mapping_api_error(exc: MappingError) -> ApiError:
    return _api_error_from_domain_error(exc)


def sort_api_error(exc: SortDecisionError) -> ApiError:
    return _api_error_from_domain_error(exc)


def csv_preview_api_error(exc: CsvPreviewError) -> ApiError:
    return _api_error_from_domain_error(exc)


def image_resolution_api_error(exc: ImageResolutionError) -> ApiError:
    return _api_error_from_domain_error(exc)


def package_api_error(exc: PackageError) -> ApiError:
    return _api_error_from_domain_error(exc)


def _api_error_from_domain_error(exc: Any) -> ApiError:
    return ApiError(
        exc.status_code,
        exc.code,
        exc.message,
        details=exc.details,
    )


def idempotency_key_from_request(request: Request) -> str | None:
    raw_value = request.headers.get("x-idempotency-key")
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    if len(value) > 128:
        raise ApiError(
            400,
            "SIRCOM_IDEMPOTENCY_KEY_INVALID",
            "Clé d'idempotence invalide.",
        )
    return value
