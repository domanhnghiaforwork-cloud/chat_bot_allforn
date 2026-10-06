import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.config import runtime
from tests.test_openai_provider import settings_for


class RuntimeCacheTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        runtime.invalidate_runtime_settings()
        runtime._cache_lock = asyncio.Lock()

    async def asyncTearDown(self):
        runtime.invalidate_runtime_settings()
        runtime._cache_lock = asyncio.Lock()

    async def test_concurrent_requests_load_settings_once(self):
        env = settings_for()
        async def load(session=None):
            await asyncio.sleep(.01)
            return env, []
        loader = AsyncMock(side_effect=load)
        with patch.object(runtime, "get_settings", return_value=env), patch.object(runtime, "effective_settings", loader):
            values = await asyncio.gather(*[runtime.runtime_settings() for _ in range(20)])
        self.assertTrue(all(value is env for value in values))
        self.assertEqual(loader.await_count, 1)

    async def test_existing_session_is_reused_and_invalidation_reloads(self):
        env = settings_for()
        changed = settings_for(user_rate_capacity=2)
        session = object()
        loader = AsyncMock(side_effect=[(env, []), (changed, [])])
        with patch.object(runtime, "get_settings", return_value=env), patch.object(runtime, "effective_settings", loader):
            self.assertIs(await runtime.runtime_settings(session), env)
            runtime.invalidate_runtime_settings()
            self.assertIs(await runtime.runtime_settings(session), changed)
        self.assertEqual(loader.await_count, 2)
        self.assertTrue(all(call.args == (session,) for call in loader.await_args_list))

    async def test_zero_ttl_does_not_reuse_stale_value(self):
        env = settings_for(runtime_settings_cache_seconds=0)
        loader = AsyncMock(return_value=(env, []))
        with patch.object(runtime, "get_settings", return_value=env), patch.object(runtime, "effective_settings", loader):
            await runtime.runtime_settings()
            await runtime.runtime_settings()
        self.assertEqual(loader.await_count, 2)
