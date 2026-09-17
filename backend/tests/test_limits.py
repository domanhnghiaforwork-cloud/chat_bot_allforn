import unittest

from app.config.limits import EDITABLE_SETTINGS, InvalidSetting, validate_value


class SettingChoiceTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
