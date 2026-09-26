import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.admin import list_settings, reset_setting, update_setting, update_settings_batch
from app.config.limits import EDITABLE_SETTINGS
from app.schemas.admin import SettingDelete, SettingUpdate, SettingsBatchUpdate
from tests.test_openai_provider import settings_for


class AdminTokenAdjustmentTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = settings_for()
        self.values = {key: getattr(self.env, definition.attr) for key, definition in EDITABLE_SETTINGS.items()}
        self.session = AsyncMock()
        self.admin = SimpleNamespace(id="test-admin")
        self.persist = AsyncMock(return_value=SimpleNamespace(version=1))

    def mocks(self):
        return (
            patch("app.api.admin.get_settings", return_value=self.env),
            patch("app.api.admin._locked_setting_values", AsyncMock(side_effect=lambda session: self.values.copy())),
            patch("app.api.admin._persist_setting", self.persist),
        )

    async def test_lowering_conversation_limit_saves_reduced_context_atomically(self):
        env, locked, persist = self.mocks()
        with env, locked, persist:
            result = await update_settings_batch(
                SettingsBatchUpdate(changes=[{"key": "MAX_CONVERSATION_TOKENS", "value": 5000}], reason="Adjust limit"),
                self.admin, self.session,
            )
        self.assertEqual(result["updated"], ["MAX_CONVERSATION_TOKENS", "CHAT_CONTEXT_WINDOW_TOKENS"])
        self.assertEqual([(call.args[1], call.args[2]) for call in self.persist.await_args_list], [
            ("MAX_CONVERSATION_TOKENS", 5000), ("CHAT_CONTEXT_WINDOW_TOKENS", 5000),
        ])
        self.session.commit.assert_awaited_once()

    async def test_batch_clamps_explicit_context_without_duplicate_writes(self):
        env, locked, persist = self.mocks()
        with env, locked, persist:
            await update_settings_batch(
                SettingsBatchUpdate(changes=[
                    {"key": "MAX_CONVERSATION_TOKENS", "value": 3000},
                    {"key": "CHAT_CONTEXT_WINDOW_TOKENS", "value": 8000},
                ], reason="Adjust limit"), self.admin, self.session,
            )
        self.assertEqual([(call.args[1], call.args[2]) for call in self.persist.await_args_list], [
            ("MAX_CONVERSATION_TOKENS", 3000), ("CHAT_CONTEXT_WINDOW_TOKENS", 3000),
        ])

    async def test_increasing_limit_does_not_increase_context(self):
        env, locked, persist = self.mocks()
        with env, locked, persist:
            result = await update_settings_batch(
                SettingsBatchUpdate(changes=[{"key": "MAX_CONVERSATION_TOKENS", "value": 200000}], reason="Adjust limit"),
                self.admin, self.session,
            )
        self.assertEqual(result["updated"], ["MAX_CONVERSATION_TOKENS"])
        self.persist.assert_awaited_once()

    async def test_single_setting_endpoint_also_reduces_context(self):
        env, locked, persist = self.mocks()
        with env, locked, persist:
            result = await update_setting("MAX_CONVERSATION_TOKENS", SettingUpdate(value=5000, reason="Adjust limit"), self.admin, self.session)
        self.assertEqual(result["value"], 5000)
        self.assertEqual(self.persist.await_count, 2)

    async def test_resetting_context_to_env_cannot_exceed_current_limit(self):
        self.values["MAX_CONVERSATION_TOKENS"] = 5000
        self.values["CHAT_CONTEXT_WINDOW_TOKENS"] = 3000
        env, locked, persist = self.mocks()
        with env, locked, persist:
            result = await reset_setting("CHAT_CONTEXT_WINDOW_TOKENS", SettingDelete(reason="Restore defaults"), self.admin, self.session)
        self.assertEqual((result["value"], result["source"]), (5000, "override"))
        self.assertEqual(self.persist.call_args.args[2], 5000)
        self.assertFalse(self.persist.call_args.args[6])

    async def test_invalid_input_does_not_write_any_changes(self):
        from fastapi import HTTPException
        env, locked, persist = self.mocks()
        with env, locked, persist, self.assertRaises(HTTPException) as caught:
            await update_settings_batch(
                SettingsBatchUpdate(changes=[{"key": "MAX_CONVERSATION_TOKENS", "value": 0}], reason="Adjust limit"),
                self.admin, self.session,
            )
        self.assertEqual(caught.exception.status_code, 422)
        self.persist.assert_not_awaited()
        self.session.commit.assert_not_awaited()

    async def test_admin_metadata_and_key_status_follow_selected_provider(self):
        for provider in ("openai", "gemini"):
            settings = settings_for(ai_provider=provider, gemini_api_key="test-gemini-key")
            with patch("app.api.admin.get_settings", return_value=settings), patch("app.api.admin.effective_settings", AsyncMock(return_value=(settings, []))):
                result = await list_settings(self.admin)
            self.assertEqual(result["provider"], provider)
            self.assertEqual(result["models"]["default"], settings.effective_default_model)
            active_key = "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
            inactive_key = "GEMINI_API_KEY" if provider == "openai" else "OPENAI_API_KEY"
            self.assertIn(active_key, result["secrets"])
            self.assertNotIn(inactive_key, result["secrets"])
            self.assertTrue(all(isinstance(value, bool) for value in result["secrets"].values()))


if __name__ == "__main__":
    unittest.main()
