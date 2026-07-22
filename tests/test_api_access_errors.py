from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import Depends, Request
from fastapi.testclient import TestClient

from sircom2026.api.errors import (
    ApiError,
    ArtifactHiddenReason,
    MASKED_PATH,
    hidden_artifact_not_found,
)
from sircom2026.api.security import (
    AccessAction,
    AccessDecision,
    AccessResource,
    ActorContext,
    require_action,
)
from sircom2026.app import create_app
from sircom2026.config import load_settings


def make_settings(tmpdir: Path, **overrides: str):
    env = {
        "SIRCOM_DATA_DIR": str(tmpdir / "data"),
        "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
        "SIRCOM_DISK_FREE_MIN_MB": "0",
    }
    env.update(overrides)
    return load_settings(env)


@dataclass
class RecordingPolicy:
    denied_actions: set[AccessAction] = field(default_factory=set)
    decisions: list[tuple[ActorContext, AccessAction, AccessResource]] = field(default_factory=list)

    def authorize(
        self,
        actor: ActorContext,
        action: AccessAction,
        resource: AccessResource,
    ) -> AccessDecision:
        self.decisions.append((actor, action, resource))
        if action in self.denied_actions:
            return AccessDecision.deny("refus test avec lot-secret")
        return AccessDecision.allow()


class ApiAccessErrorsTest(unittest.TestCase):
    def test_access_actions_cover_lot_and_artifact_operations(self) -> None:
        self.assertGreaterEqual(
            {action.value for action in AccessAction},
            {
                "lot:create",
                "lot:read",
                "lot:update",
                "lot:download",
                "lot:delete",
                "artifact:create",
                "artifact:read",
                "artifact:update",
                "artifact:download",
                "artifact:delete",
            },
        )

    def test_local_access_policy_allows_protected_config_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.get("/api/config/limits")

        self.assertEqual(response.status_code, 200)
        self.assertIn("limits", response.json())

    def test_mutating_request_from_foreign_origin_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.post(
                "/api/lots",
                headers={"Origin": "https://example.invalid"},
                json={"title": "Lot pirate"},
            )
            list_response = client.get("/api/lots")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_ACCESS_DENIED")
        self.assertEqual(list_response.json()["pagination"]["total"], 0)

    def test_mutating_request_from_same_origin_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.post(
                "/api/lots",
                headers={"Origin": "http://testserver"},
                json={"title": "Lot local"},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["lot"]["title"], "Lot local")

    def test_mutating_request_from_foreign_referer_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.post(
                "/api/lots",
                headers={"Referer": "https://example.invalid/piege"},
                json={"title": "Lot pirate"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_ACCESS_DENIED")

    def test_local_access_policy_refuses_non_loopback_bind_without_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp), SIRCOM_BIND_HOST="0.0.0.0")
            app = create_app(settings)

            @app.get("/api/test/non-loopback/lots/{lot_id}")
            async def non_loopback_probe(
                _actor: ActorContext = Depends(require_action(AccessAction.LOT_READ)),
            ) -> dict[str, str]:
                return {"status": "visible"}

            client = TestClient(app)
            health_response = client.get("/health")
            response = client.get("/api/test/non-loopback/lots/lot-expose-secret")

        payload = response.json()
        serialized = str(payload)
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            payload,
            {
                "error": {
                    "code": "SIRCOM_ACCESS_DENIED",
                    "message": "Acces refuse.",
                }
            },
        )
        self.assertNotIn("lot-expose-secret", serialized)
        self.assertNotIn(str(settings.data_dir), serialized)

    def test_policy_can_refuse_access_without_changing_route(self) -> None:
        policy = RecordingPolicy({AccessAction.CONFIG_READ})
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp)), access_policy=policy))

            response = client.get(
                "/api/config/limits",
                headers={"X-Correlation-ID": "corr-ticket-02"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["x-correlation-id"], "corr-ticket-02")
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "SIRCOM_ACCESS_DENIED",
                    "message": "Acces refuse.",
                    "correlation_id": "corr-ticket-02",
                }
            },
        )
        self.assertEqual(len(policy.decisions), 1)
        actor, action, resource = policy.decisions[0]
        self.assertEqual(actor.actor_id, "local-user")
        self.assertEqual(actor.mode, "local")
        self.assertEqual(actor.correlation_id, "corr-ticket-02")
        self.assertEqual(action, AccessAction.CONFIG_READ)
        self.assertEqual(resource, AccessResource())

    def test_access_refusal_does_not_expose_other_lot_data(self) -> None:
        policy = RecordingPolicy({AccessAction.LOT_READ})
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(make_settings(Path(tmp)), access_policy=policy)

            @app.get("/api/test/lots/{lot_id}")
            async def read_lot(
                _actor: ActorContext = Depends(require_action(AccessAction.LOT_READ)),
            ) -> dict[str, str]:
                return {"status": "visible"}

            client = TestClient(app)
            response = client.get("/api/test/lots/lot-secret")

        serialized = str(response.json())
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("lot-secret", serialized)
        self.assertNotIn("refus test", serialized)
        self.assertEqual(policy.decisions[0][2].lot_id, "lot-secret")

    def test_structured_error_sanitizes_internal_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            app = create_app(settings)

            @app.get("/api/test/path-error")
            async def path_error(
                _actor: ActorContext = Depends(require_action(AccessAction.CONFIG_READ)),
            ) -> dict[str, str]:
                raise ApiError(
                    400,
                    "SIRCOM_TEST_PATH",
                    f"Erreur de test pour {settings.data_dir / 'lot-secret' / 'input.xlsx'}.",
                    details={
                        "upload_path": settings.data_dir / "lot-secret" / "input.xlsx",
                        "relative_path": ".sircom2026-data/lots/lot-secret/input.xlsx",
                        "sqlite_path": str(settings.sqlite_path),
                        "safe_code": "EXCEL_HIDDEN_COLUMNS",
                    },
                )

            client = TestClient(app)
            response = client.get("/api/test/path-error")

        payload = response.json()
        serialized = str(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"]["code"], "SIRCOM_TEST_PATH")
        self.assertEqual(payload["error"]["message"], f"Erreur de test pour {MASKED_PATH}.")
        self.assertEqual(payload["error"]["details"]["upload_path"], MASKED_PATH)
        self.assertEqual(payload["error"]["details"]["relative_path"], MASKED_PATH)
        self.assertEqual(payload["error"]["details"]["sqlite_path"], MASKED_PATH)
        self.assertEqual(payload["error"]["details"]["safe_code"], "EXCEL_HIDDEN_COLUMNS")
        self.assertNotIn(str(settings.data_dir), serialized)
        self.assertNotIn(str(settings.sqlite_path), serialized)

    def test_http_errors_use_structured_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.get("/api/does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "SIRCOM_NOT_FOUND",
                    "message": "Ressource introuvable.",
                }
            },
        )

    def test_hidden_artifact_404_is_publicly_indistinguishable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(make_settings(Path(tmp)))

            @app.get("/api/test/lots/{lot_id}/downloads/{artifact_id}/{reason}")
            async def download_probe(lot_id: str, artifact_id: str, reason: str, request: Request):
                raise hidden_artifact_not_found(
                    lot_id=lot_id,
                    artifact_id=artifact_id,
                    reason=ArtifactHiddenReason(reason),
                    request=request,
                )

            client = TestClient(app)
            responses = []
            for reason in ("absent", "supprime", "obsolete", "autre_lot"):
                with self.assertLogs("sircom2026.api.errors", level="INFO") as captured:
                    response = client.get(
                        f"/api/test/lots/lot-secret/downloads/artifact-secret/{reason}"
                    )
                responses.append(response.json())
                log_output = "\n".join(captured.output)
                self.assertIn(reason, log_output)
                self.assertNotIn("lot-secret", log_output)
                self.assertNotIn("artifact-secret", log_output)

        self.assertTrue(all(response == responses[0] for response in responses))
        self.assertEqual(
            responses[0],
            {
                "error": {
                    "code": "SIRCOM_ARTIFACT_NOT_FOUND",
                    "message": "Artefact introuvable.",
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
