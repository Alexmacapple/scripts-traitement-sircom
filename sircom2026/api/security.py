from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from urllib.parse import urlsplit

from fastapi import Depends, Request

from sircom2026.api.errors import ApiError, correlation_id_from_request


class AccessAction(str, Enum):
    CONFIG_READ = "config:read"
    LOT_CREATE = "lot:create"
    LOT_READ = "lot:read"
    LOT_UPDATE = "lot:update"
    LOT_DOWNLOAD = "lot:download"
    LOT_DELETE = "lot:delete"
    ARTIFACT_CREATE = "artifact:create"
    ARTIFACT_READ = "artifact:read"
    ARTIFACT_UPDATE = "artifact:update"
    ARTIFACT_DOWNLOAD = "artifact:download"
    ARTIFACT_DELETE = "artifact:delete"


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    mode: str
    display_name: str
    correlation_id: str | None = None


@dataclass(frozen=True)
class AccessResource:
    lot_id: str | None = None
    artifact_id: str | None = None

    @classmethod
    def from_request(cls, request: Request) -> AccessResource:
        return cls(
            lot_id=_string_path_param(request, "lot_id"),
            artifact_id=_string_path_param(request, "artifact_id"),
        )


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str | None = None

    @classmethod
    def allow(cls) -> AccessDecision:
        return cls(True)

    @classmethod
    def deny(cls, reason: str | None = None) -> AccessDecision:
        return cls(False, reason)


class AccessPolicy(Protocol):
    def authorize(
        self,
        actor: ActorContext,
        action: AccessAction,
        resource: AccessResource,
    ) -> AccessDecision:
        ...


class LocalAccessPolicy:
    def __init__(self, bind_host: str = "127.0.0.1") -> None:
        self.bind_host = bind_host

    def authorize(
        self,
        actor: ActorContext,
        action: AccessAction,
        resource: AccessResource,
    ) -> AccessDecision:
        if not _is_loopback_bind_host(self.bind_host):
            return AccessDecision.deny("bind_host_not_loopback")
        return AccessDecision.allow()


def get_actor_context(request: Request) -> ActorContext:
    return ActorContext(
        actor_id="local-user",
        mode="local",
        display_name="Utilisateur local",
        correlation_id=correlation_id_from_request(request),
    )


def get_access_policy(request: Request) -> AccessPolicy:
    return request.app.state.access_policy


def require_action(action: AccessAction):
    async def dependency(
        request: Request,
        actor: ActorContext = Depends(get_actor_context),
    ) -> ActorContext:
        local_host_reason = _local_host_header_reason(request)
        if local_host_reason is not None:
            raise ApiError(
                403,
                "SIRCOM_ACCESS_DENIED",
                "Acces refuse.",
            )
        cross_origin_reason = _unsafe_cross_origin_reason(request)
        if cross_origin_reason is not None:
            raise ApiError(
                403,
                "SIRCOM_ACCESS_DENIED",
                "Acces refuse.",
            )
        resource = AccessResource.from_request(request)
        policy = get_access_policy(request)
        decision = policy.authorize(actor, action, resource)
        if not decision.allowed:
            raise ApiError(
                403,
                "SIRCOM_ACCESS_DENIED",
                "Acces refuse.",
            )
        request.state.actor_context = actor
        request.state.access_action = action
        request.state.access_resource = resource
        return actor

    return dependency


def _string_path_param(request: Request, name: str) -> str | None:
    value = request.path_params.get(name)
    if value is None:
        return None
    return str(value)


def _is_loopback_bind_host(bind_host: str) -> bool:
    normalized = bind_host.strip().lower()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    return normalized in {"127.0.0.1", "localhost", "::1"}


_UNSAFE_METHODS = {"DELETE", "PATCH", "POST", "PUT"}
_LOCAL_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1", "testserver"}


def _local_host_header_reason(request: Request) -> str | None:
    host_header = request.headers.get("host")
    if not host_header:
        return "host_missing"
    parts = urlsplit(f"{request.url.scheme}://{host_header}")
    if not parts.hostname:
        return "host_malformed"
    if parts.hostname.lower() not in _LOCAL_ALLOWED_HOSTS:
        return "host_not_allowed"
    if _normalized_port(parts) is None:
        return "host_port_invalid"
    return None


def _unsafe_cross_origin_reason(request: Request) -> str | None:
    if request.method.upper() not in _UNSAFE_METHODS:
        return None
    for header_name in ("origin", "referer"):
        source = request.headers.get(header_name)
        if source and not _source_matches_request_origin(source, request):
            return f"{header_name}_not_same_origin"
    return None


def _source_matches_request_origin(source: str, request: Request) -> bool:
    source = source.strip()
    if not source or source == "null" or any(character.isspace() for character in source):
        return False
    source_parts = urlsplit(source)
    if source_parts.scheme not in {"http", "https"} or not source_parts.hostname:
        return False
    request_parts = _request_origin_parts(request)
    if request_parts is None:
        return False
    request_scheme, request_host, request_port = request_parts
    source_port = _normalized_port(source_parts)
    if source_port is None:
        return False
    return (
        source_parts.scheme == request_scheme
        and source_parts.hostname.lower() == request_host
        and source_port == request_port
    )


def _request_origin_parts(request: Request) -> tuple[str, str, int] | None:
    host_header = request.headers.get("host")
    if not host_header:
        return None
    parts = urlsplit(f"{request.url.scheme}://{host_header}")
    if not parts.hostname:
        return None
    request_port = _normalized_port(parts)
    if request_port is None:
        return None
    return request.url.scheme, parts.hostname.lower(), request_port


def _normalized_port(parts) -> int | None:
    try:
        port = parts.port
    except ValueError:
        return None
    if port is not None:
        return port
    return 443 if parts.scheme == "https" else 80
