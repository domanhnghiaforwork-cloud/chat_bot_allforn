import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.schemas.generation import ChatJobRequest


class ChatCommandValidationTest(unittest.TestCase):
    def test_sync_chat_rejects_local_command(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest.model_validate(
                {
                    "conversation_id": uuid4(),
                    "message": "  /token  ",
                }
            )

    def test_async_chat_rejects_local_command(self) -> None:
        with self.assertRaises(ValidationError):
            ChatJobRequest.model_validate(
                {
                    "conversation_id": uuid4(),
                    "message": "/context",
                    "client_request_id": uuid4(),
                }
            )

    def test_regular_message_is_still_accepted(self) -> None:
        payload = ChatRequest.model_validate(
            {
                "conversation_id": uuid4(),
                "message": "Giải thích cách tính token",
            }
        )

        self.assertEqual(payload.message, "Giải thích cách tính token")


if __name__ == "__main__":
    unittest.main()
