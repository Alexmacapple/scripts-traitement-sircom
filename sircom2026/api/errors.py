from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


LOGGER = logging.getLogger(__name__)
MASKED_PATH = "[chemin masque]"
_POSIX_PATH_RE = re.compile(r"(?<![:\w])(?:~|/)[^\s'\"<>]+(?:/[^\s'\"<>]+)+")
_WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/][^\s'\"<>]+")
_SENSITIVE_DETAIL_KEY_PARTS = ("path", "chemin", "file", "filename", "directory", "dir", "sqlite")
_TRAILING_PATH_PUNCTUATION = ".,;:!?)"


class ArtifactHiddenReason(str, Enum):
    ABSENT = "absent"
    DELETED = "supprime"
    OBSOLETE = "obsolete"
    OTHER_LOT = "autre_lot"


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = dict(headers or {})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


def correlation_id_from_request(request: Request) -> str | None:
    raw_value = request.headers.get("x-correlation-id") or request.headers.get("x-request-id")
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    return value[:128]


def hidden_artifact_not_found(
    *,
    lot_id: str,
    artifact_id: str,
    reason: ArtifactHiddenReason,
    request: Request | None = None,
) -> ApiError:
    event: dict[str, str] = {
        "event": "artifact_hidden_not_found",
        "reason": reason.value if isinstance(reason, ArtifactHiddenReason) else "unknown",
        "lot_id_hash": _hash_identifier(lot_id),
        "artifact_id_hash": _hash_identifier(artifact_id),
    }
    if request is not None:
        correlation_id = correlation_id_from_request(request)
        if correlation_id is not None:
            event["correlation_id"] = correlation_id

    LOGGER.info("technical_event=%s", json.dumps(event, sort_keys=True))
    return ApiError(
        404,
        "SIRCOM_ARTIFACT_NOT_FOUND",
        "Artefact introuvable.",
    )


async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=exc.headers,
    )


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = {
        "errors": [
            {
                "loc": list(error.get("loc", ())),
                "msg": error.get("msg", "Erreur de validation."),
                "type": error.get("type", "validation_error"),
            }
            for error in exc.errors()
        ]
    }
    return _error_response(
        request,
        status_code=422,
        code="SIRCOM_VALIDATION_ERROR",
        message="Requête invalide.",
        details=details,
    )


async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        code = str(detail["code"])
        message = str(detail["message"])
        details = detail.get("details")
    elif exc.status_code == 404:
        code = "SIRCOM_NOT_FOUND"
        message = "Ressource introuvable."
        details = None
    elif exc.status_code == 405:
        code = "SIRCOM_METHOD_NOT_ALLOWED"
        message = "Méthode HTTP non autorisée."
        details = None
    else:
        code = "SIRCOM_HTTP_ERROR"
        message = "Erreur HTTP."
        details = None

    return _error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
        headers=getattr(exc, "headers", None),
    )


async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    LOGGER.exception("technical_event=unexpected_api_error")
    return _error_response(
        request,
        status_code=500,
        code="SIRCOM_INTERNAL_ERROR",
        message="Erreur interne inattendue.",
    )


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": _mask_paths_in_text(message),
    }

    safe_details = _sanitize_details(details)
    if safe_details not in (None, {}, []):
        error["details"] = safe_details

    response_headers = dict(headers or {})
    correlation_id = correlation_id_from_request(request)
    if correlation_id is not None:
        error["correlation_id"] = correlation_id
        response_headers["X-Correlation-ID"] = correlation_id

    return JSONResponse(
        status_code=status_code,
        content={"error": error},
        headers=response_headers,
    )


def _sanitize_details(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _is_sensitive_detail_key(key) and value not in (None, "", {}, []):
        return MASKED_PATH
    if isinstance(value, Path):
        return MASKED_PATH
    if isinstance(value, str):
        return _mask_paths_in_text(value)
    if isinstance(value, Mapping):
        return {str(child_key): _sanitize_details(child, key=str(child_key)) for child_key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_sanitize_details(child) for child in value]
    return value


def _looks_like_absolute_path(value: str) -> bool:
    if value.startswith(("/", "~")):
        return True
    return len(value) > 2 and value[1] == ":" and value[2] in {"/", "\\"}


def _mask_paths_in_text(value: str) -> str:
    if _looks_like_absolute_path(value) and not any(character.isspace() for character in value):
        return MASKED_PATH
    value = _POSIX_PATH_RE.sub(_masked_path_replacement, value)
    return _WINDOWS_PATH_RE.sub(_masked_path_replacement, value)


def _is_sensitive_detail_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in _SENSITIVE_DETAIL_KEY_PARTS)


def _masked_path_replacement(match: re.Match[str]) -> str:
    matched_path = match.group(0)
    suffix = ""
    while matched_path and matched_path[-1] in _TRAILING_PATH_PUNCTUATION:
        suffix = matched_path[-1] + suffix
        matched_path = matched_path[:-1]
    return MASKED_PATH + suffix


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
