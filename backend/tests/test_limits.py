import unittest

from app.config.limits import (
    EDITABLE_SETTINGS,
    InvalidSetting,
    validate_relations,
    validate_value,
)


class SettingChoiceTest(unittest.TestCase):
    def test_token_settings_are_first(self) -> None:
        self.assertEqual(
            list(EDITABLE_SETTINGS)[:3],
            [
                "CHAT_CONTEXT_WINDOW_TOKENS",
                "SUMMARY_CONTEXT_WINDOW_TOKENS",
                "MAX_CONVERSATION_TOKENS",
            ],
        )

    def test_all_non_numeric_settings_have_choices(self) -> None:
        for definition in EDITABLE_SETTINGS.values():
            if definition.value_type not in {"integer", "number"}:
                self.assertTrue(definition.choices, definition.key)

    def test_accepts_supported_model(self) -> None:
        definition = EDITABLE_SETTINGS["DEFAULT_MODEL_NAME"]
        self.assertEqual(
            validate_value(definition, "gemini-3.1-flash-lite"),
            "gemini-3.1-flash-lite",
        )

    def test_rejects_model_outside_choices(self) -> None:
        definition = EDITABLE_SETTINGS["DEFAULT_MODEL_NAME"]
        with self.assertRaises(InvalidSetting):
            validate_value(definition, "gemini-other")

    def test_boolean_has_explicit_choices(self) -> None:
        definition = EDITABLE_SETTINGS["FALLBACK_ENABLED"]
        self.assertEqual(definition.choices, ((True, "Bật"), (False, "Tắt")))

    def test_conversation_limit_cannot_be_smaller_than_chat_context(self) -> None:
        values = {
            "CHAT_CONTEXT_WINDOW_TOKENS": 10_000,
            "SUMMARY_CONTEXT_WINDOW_TOKENS": 15_000,
            "MAX_CONVERSATION_TOKENS": 9_999,
            "GEMINI_RETRY_INITIAL_DELAY_SECONDS": 1,
            "GEMINI_RETRY_MAX_DELAY_SECONDS": 20,
            "GEMINI_MAX_RETRY_ELAPSED_SECONDS": 90,
            "GEMINI_REQUEST_TIMEOUT_SECONDS": 60,
        }
        with self.assertRaises(InvalidSetting):
            validate_relations(values, 0.15)

    def test_summary_context_must_leave_room_for_summary_output(self) -> None:
        values = {
            "CHAT_CONTEXT_WINDOW_TOKENS": 10_000,
            "SUMMARY_CONTEXT_WINDOW_TOKENS": 1_500,
            "MAX_CONVERSATION_TOKENS": 100_000,
            "GEMINI_RETRY_INITIAL_DELAY_SECONDS": 1,
            "GEMINI_RETRY_MAX_DELAY_SECONDS": 20,
            "GEMINI_MAX_RETRY_ELAPSED_SECONDS": 90,
            "GEMINI_REQUEST_TIMEOUT_SECONDS": 60,
        }
        with self.assertRaises(InvalidSetting):
            validate_relations(values, 0.15)


if __name__ == "__main__":
    unittest.main()
