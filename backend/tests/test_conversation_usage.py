import unittest
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch
from uuid import uuid4

from app.services.conversation import get_conversation_token_usage


class ConversationTokenUsageTest(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.conversation.runtime_settings", new_callable=AsyncMock)
    @patch("app.services.conversation.conversations.get_owned", new_callable=AsyncMock)
    async def test_returns_conversation_and_context_budgets(
        self,
        get_owned: AsyncMock,
        runtime_settings: AsyncMock,
    ) -> None:
        get_owned.return_value = SimpleNamespace(
            messages=[
                SimpleNamespace(content="a" * 30),
                SimpleNamespace(content="b" * 60),
            ]
        )
        runtime_settings.return_value = SimpleNamespace(
            max_conversation_tokens=100_000,
            chat_context_window_tokens=10_000,
            max_chat_input_tokens=7_500,
            max_chat_output_tokens=2_500,
        )

        conversation_id = uuid4()
        user_id = uuid4()
        usage = await get_conversation_token_usage(
            AsyncMock(), conversation_id, user_id
        )

        self.assertIsNotNone(usage)
        assert usage is not None
        self.assertEqual(usage["current_tokens"], 30)
        self.assertEqual(usage["remaining_tokens"], 99_970)
        self.assertEqual(usage["chat_context_window_tokens"], 10_000)
        self.assertEqual(usage["max_chat_input_tokens"], 7_500)
        self.assertEqual(usage["max_chat_output_tokens"], 2_500)
        get_owned.assert_awaited_once_with(
            ANY,
            conversation_id,
            user_id,
            with_messages=True,
        )


if __name__ == "__main__":
    unittest.main()
