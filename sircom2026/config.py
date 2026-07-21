from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when SIRCOM_* configuration cannot be parsed safely."""


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    sqlite_path: Path
    retention_days: int
    max_excel_mb: int
    max_zip_mb: int
    max_image_count: int
    max_image_mb: int
    max_unzipped_mb: int
    indesign_image_root: str
    bind_host: str
    port: int
    worker_enabled: bool
    worker_id: str
    max_active_jobs: int
    worker_poll_seconds: int
    worker_lease_ttl_seconds: int
    worker_heartbeat_seconds: int
    disk_free_min_mb: int
    sqlite_busy_timeout_ms: int
    artifact_pending_ttl_seconds: int

    def public_limits(self) -> dict[str, object]:
        return {
            "excel": {"max_mb": self.max_excel_mb},
            "zip": {"max_mb": self.max_zip_mb, "max_unzipped_mb": self.max_unzipped_mb},
            "images": {"max_count": self.max_image_count, "max_mb": self.max_image_mb},
            "retention": {"days": self.retention_days},
            "worker": {
                "enabled": self.worker_enabled,
                "max_active_jobs": self.max_active_jobs,
                "poll_seconds": self.worker_poll_seconds,
                "lease_ttl_seconds": self.worker_lease_ttl_seconds,
                "heartbeat_seconds": self.worker_heartbeat_seconds,
            },
            "disk": {"free_min_mb": self.disk_free_min_mb},
            "artifacts": {"pending_ttl_seconds": self.artifact_pending_ttl_seconds},
        }


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if env is None else env

    data_dir = _path(values, "SIRCOM_DATA_DIR", ".sircom2026-data")
    sqlite_path = _path(values, "SIRCOM_SQLITE_PATH", str(data_dir / "sircom.sqlite3"))

    return Settings(
        data_dir=data_dir,
        sqlite_path=sqlite_path,
        retention_days=_int(values, "SIRCOM_RETENTION_DAYS", 7, minimum=1),
        max_excel_mb=_int(values, "SIRCOM_MAX_EXCEL_MB", 50, minimum=1),
        max_zip_mb=_int(values, "SIRCOM_MAX_ZIP_MB", 1024, minimum=1),
        max_image_count=_int(values, "SIRCOM_MAX_IMAGE_COUNT", 1500, minimum=1),
        max_image_mb=_int(values, "SIRCOM_MAX_IMAGE_MB", 50, minimum=1),
        max_unzipped_mb=_int(values, "SIRCOM_MAX_UNZIPPED_MB", 3072, minimum=1),
        indesign_image_root=_text(
            values,
            "SIRCOM_INDESIGN_IMAGE_ROOT",
            "/Users/victoria/Documents/export-jpg-resize",
        ),
        bind_host=_text(values, "SIRCOM_BIND_HOST", "127.0.0.1"),
        port=_int(values, "SIRCOM_PORT", 8000, minimum=1, maximum=65535),
        worker_enabled=_bool(values, "SIRCOM_WORKER_ENABLED", True),
        worker_id=_text(values, "SIRCOM_WORKER_ID", "local-1"),
        max_active_jobs=_int(values, "SIRCOM_MAX_ACTIVE_JOBS", 1, minimum=1),
        worker_poll_seconds=_int(values, "SIRCOM_WORKER_POLL_SECONDS", 2, minimum=1),
        worker_lease_ttl_seconds=_int(
            values,
            "SIRCOM_WORKER_LEASE_TTL_SECONDS",
            300,
            minimum=1,
        ),
        worker_heartbeat_seconds=_int(
            values,
            "SIRCOM_WORKER_HEARTBEAT_SECONDS",
            30,
            minimum=1,
        ),
        disk_free_min_mb=_int(values, "SIRCOM_DISK_FREE_MIN_MB", 5120, minimum=0),
        sqlite_busy_timeout_ms=_int(values, "SIRCOM_SQLITE_BUSY_TIMEOUT_MS", 5000, minimum=0),
        artifact_pending_ttl_seconds=_int(
            values,
            "SIRCOM_ARTIFACT_PENDING_TTL_SECONDS",
            3600,
            minimum=1,
        ),
    )


def _path(env: Mapping[str, str], name: str, default: str) -> Path:
    value = env.get(name, default)
    if not str(value).strip():
        raise ConfigError(f"{name} must not be empty.")
    return Path(value).expanduser()


def _text(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(name, default)
    if not str(value).strip():
        raise ConfigError(f"{name} must not be empty.")
    return str(value)


def _int(
    env: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    raw_value = env.get(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer.") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be greater than or equal to {minimum}.")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be less than or equal to {maximum}.")
    return value


def _bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw_value = env.get(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "oui"}:
        return True
    if normalized in {"0", "false", "no", "off", "non"}:
        return False
    raise ConfigError(f"{name} must be a boolean.")
