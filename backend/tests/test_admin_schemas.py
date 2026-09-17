import unittest

from pydantic import ValidationError

from app.schemas.admin import SettingsBatchUpdate


class SettingsBatchUpdateTest(unittest.TestCase):
    def test_accepts_multiple_unique_changes(self) -> None:
        payload = SettingsBatchUpdate.model_validate(
            {
                "changes": [
                    {"key": "DEFAULT_MODEL_RPM", "value": 10},
                    {"key": "SUMMARY_MODEL_NAME", "reset": True},
                ],
                "reason": "Điều chỉnh quota",
            }
        )
        self.assertEqual(len(payload.changes), 2)

    def test_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(ValidationError):
            SettingsBatchUpdate.model_validate(
                {
                    "changes": [
                        {"key": "DEFAULT_MODEL_RPM", "value": 10},
                        {"key": "DEFAULT_MODEL_RPM", "value": 20},
                    ],
                    "reason": "Điều chỉnh quota",
                }
            )


if __name__ == "__main__":
    unittest.main()
