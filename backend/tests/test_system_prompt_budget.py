import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.config.prompts import SYSTEM_PROMPT
from app.llm.gateway import LLMGateway
from app.memory.summary import prepare_memory
from tests.test_openai_provider import settings_for


class SystemPromptBudgetTest(unittest.IsolatedAsyncioTestCase):
    def test_ratios_sum_to_max_input_ratio(self):
        settings = settings_for()
        self.assertAlmostEqual(
            settings.max_history_recent_messages_ratio
            + settings.max_history_summary_ratio
            + settings.max_user_input_ratio
            + (settings.max_system_prompt_ratio or 0.0),
            settings.max_input_ratio,
        )
        self.assertAlmostEqual(settings.max_input_ratio + settings.max_output_ratio, 1.0)

    def test_system_prompt_enforces_safety_floor(self):
        # Even if configured with a tiny budget, floor guarantees enough space for SYSTEM_PROMPT
        settings = settings_for(max_system_prompt_tokens=10)
        self.assertGreaterEqual(settings.max_system_prompt_tokens, len(SYSTEM_PROMPT) // 3)

    async def test_low_chat_context_window_does_not_break_system_prompt(self):
        # Admin lowers CHAT_CONTEXT_WINDOW_TOKENS to 1000
        settings = settings_for(chat_context_window_tokens=1000, max_conversation_tokens=2000)
        self.assertEqual(settings.chat_context_window_tokens, 1000)
        # System prompt budget remains dedicated (e.g., 500)
        self.assertGreaterEqual(settings.max_system_prompt_tokens, 250)

        session = AsyncMock()
        session.get.return_value = None
        gateway = LLMGateway(uuid4())
        # measure_text_tokens for SYSTEM_PROMPT returns its real estimate (~206 tokens)
        gateway.measure_message_tokens = AsyncMock(return_value=10)
        gateway.measure_context_tokens = AsyncMock(return_value=100)

        history = [
            SimpleNamespace(role="user", content="Hello"),
            SimpleNamespace(role="assistant", content="Hi"),
        ]
        # Must not raise "System Prompt vượt ngân sách token"
        memory = await prepare_memory(session, uuid4(), history, "Xin chào", gateway, settings)
        self.assertIsNotNone(memory)
        self.assertEqual(len(memory.recent_messages), 2)


if __name__ == "__main__":
    unittest.main()
