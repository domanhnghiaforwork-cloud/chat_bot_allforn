import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.llm.gateway import LLMGateway
from app.llm.generation import estimate_tokens, should_count_exactly


class TokenEstimationTest(unittest.TestCase):
    def test_estimate_is_conservative_by_character_count(self) -> None:
        self.assertEqual(estimate_tokens("a" * 30), 10)

    def test_exact_count_starts_at_95_percent(self) -> None:
        self.assertFalse(should_count_exactly(949, 1000, 0.95))
        self.assertTrue(should_count_exactly(950, 1000, 0.95))
        self.assertTrue(should_count_exactly(1000, 1000, 0.95))


class HybridTokenMeasureTest(unittest.IsolatedAsyncioTestCase):
    async def test_short_text_does_not_call_provider_tokenizer(self) -> None:
        gateway = LLMGateway(uuid4())
        gateway.count_text_tokens = AsyncMock(return_value=10)

        measured = await gateway.measure_text_tokens("a" * 30, 100)

        self.assertEqual(measured, 10)
        gateway.count_text_tokens.assert_not_awaited()

    async def test_near_limit_calls_provider_tokenizer(self) -> None:
        gateway = LLMGateway(uuid4())
        gateway.count_text_tokens = AsyncMock(return_value=93)

        measured = await gateway.measure_text_tokens("a" * 285, 100)

        self.assertEqual(measured, 93)
        gateway.count_text_tokens.assert_awaited_once_with("a" * 285, "chat")


if __name__ == "__main__":
    unittest.main()
