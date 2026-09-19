import unittest
from types import SimpleNamespace

import httpx
from sqlalchemy import text

from app.db.database import engine
from app.api.dependencies import get_current_user, require_admin
from app.main import app
from app.redis_client import close_redis_clients


class ApiSmokeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        await close_redis_clients()
        await engine.dispose()

    async def test_live_and_protected_routes(self) -> None:
        live = await self.client.get("/health/live")
        self.assertEqual(live.status_code, 200)
        public_config = await self.client.get("/config")
        self.assertEqual(public_config.status_code, 200)
        self.assertEqual(public_config.json(), {"name_chatbot": "OLP AI"})
        self.assertIn(
            "/conversations/{conversation_id}/token-usage",
            (await self.client.get("/openapi.json")).json()["paths"],
        )
        self.assertEqual((await self.client.get("/users/me")).status_code, 401)
        self.assertEqual((await self.client.get("/admin/settings")).status_code, 401)
        auth_fields = (await self.client.get("/openapi.json")).json()["components"][
            "schemas"
        ]["AuthCredentials"]["properties"]
        self.assertNotIn("role", auth_fields)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="user")
        try:
            self.assertEqual((await self.client.get("/admin/settings")).status_code, 403)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_ready_reports_dependencies(self) -> None:
        response = await self.client.get("/health/ready")
        self.assertIn(response.status_code, {200, 503})
        self.assertEqual(set(response.json()), {"status", "postgres", "redis"})
        async with engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            advisory_lock = await connection.scalar(
                text(
                    "SELECT pg_try_advisory_xact_lock("
                    "hashtextextended(:lock_name, 0))"
                ),
                {"lock_name": "v4.2-smoke"},
            )
            invalid_roles = await connection.scalar(
                text(
                    "SELECT COUNT(*) FROM users "
                    "WHERE role IS NULL OR role NOT IN ('user', 'admin')"
                )
            )
        self.assertEqual(revision, "20260917_02")
        self.assertTrue(advisory_lock)
        self.assertEqual(invalid_roles, 0)
        app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
        try:
            admin_settings = await self.client.get("/admin/settings")
            self.assertEqual(admin_settings.status_code, 200)
            self.assertEqual(
                [item["key"] for item in admin_settings.json()["settings"][:3]],
                [
                    "CHAT_CONTEXT_WINDOW_TOKENS",
                    "SUMMARY_CONTEXT_WINDOW_TOKENS",
                    "MAX_CONVERSATION_TOKENS",
                ],
            )
            self.assertTrue(
                all(isinstance(value, bool) for value in admin_settings.json()["secrets"].values())
            )
            invalid = await self.client.patch(
                "/admin/settings/WORKER_CONCURRENCY",
                json={"value": 0, "reason": "smoke test"},
            )
            self.assertEqual(invalid.status_code, 422)
            secret = await self.client.patch(
                "/admin/settings/DATABASE_URL",
                json={"value": "hidden", "reason": "smoke test"},
            )
            self.assertEqual(secret.status_code, 404)
        finally:
            app.dependency_overrides.pop(require_admin, None)


if __name__ == "__main__":
    unittest.main()
