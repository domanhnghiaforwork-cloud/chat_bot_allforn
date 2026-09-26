import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from google.genai import types
from pydantic import ValidationError

from app.config.settings import Settings
from app.llm.errors import LLMError, normalize_provider_error
from app.llm.gateway import LLMGateway
from app.llm.openai_provider import count_openai_tokens, generate_openai
from app.memory.context_builder import ChatContext
from app.rate_limit.model_limiter import ModelLimiter, QuotaReservation
from app.routing.model_router import route_model


def settings_for(**changes) -> Settings:
    values = {
        key.lower(): value
        for key, value in dotenv_values(Path(__file__).parents[1] / ".env.example").items()
        if value is not None
    }
    values.update(ai_provider="openai", openai_api_key="test-key", gemini_api_key="")
    values.update(changes)
    return Settings(_env_file=None, **values)


def contents():
    return [
        types.Content(role="user", parts=[types.Part.from_text(text="Question")]),
        types.Content(role="model", parts=[types.Part.from_text(text="Previous answer")]),
        types.Content(role="user", parts=[types.Part.from_text(text="Follow up")]),
    ]


def completed(text="Hello"):
    return {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        "usage": {"input_tokens": 42, "output_tokens": 7},
    }


def mock_client(handler):
    return patch("app.llm.openai_provider.openai_client", side_effect=lambda settings: httpx.AsyncClient(
        base_url="https://api.openai.com/v1/", transport=httpx.MockTransport(handler),
    ))


def sse(events):
    return "".join("data: " + json.dumps(event) + "\n\n" for event in events)


class ProviderSettingsTest(unittest.TestCase):
    def test_openai_ignores_old_gemini_model_names(self):
        settings = settings_for()
        self.assertEqual(route_model("chat", None, settings), "gpt-4.1-mini")
        self.assertEqual(route_model("summary", None, settings), "gpt-4.1-mini")
        self.assertEqual(route_model("chat", "advanced", settings), "gpt-4.1-mini")

    def test_openai_allows_custom_model_and_role_models(self):
        settings = settings_for(openai_model="custom-response-model", openai_summary_model="summary-model", openai_advanced_model="advanced-model")
        self.assertEqual(settings.effective_default_model, "custom-response-model")
        self.assertEqual(settings.effective_summary_model, "summary-model")
        self.assertEqual(settings.effective_advanced_model, "advanced-model")

    def test_gemini_keeps_existing_routing_without_openai_key(self):
        settings = settings_for(ai_provider="gemini", gemini_api_key="test-gemini-key", openai_api_key="")
        self.assertEqual(settings.effective_default_model, "gemini-3.5-flash-lite")
        self.assertEqual(settings.effective_summary_model, "gemini-3.1-flash-lite")

    def test_active_provider_requires_key(self):
        for provider in ("gemini", "openai"):
            with self.subTest(provider=provider), self.assertRaises(ValidationError):
                settings_for(ai_provider=provider, openai_api_key="", gemini_api_key="")

    def test_invalid_provider_and_partial_quotas_rejected(self):
        for changes in ({"ai_provider": "other"}, {"openai_rpm": 10}, {"openai_model": " "}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                settings_for(**changes)

    def test_openai_error_mapping_and_no_retry_after_delta(self):
        for status, code, retryable in ((401, "PROVIDER_AUTH_ERROR", False), (404, "MODEL_UNAVAILABLE", False), (429, "PROVIDER_RATE_LIMITED", True), (503, "PROVIDER_UNAVAILABLE", True)):
            response = httpx.Response(status, headers={"Retry-After": "12"}, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
            exc = httpx.HTTPStatusError("test", request=response.request, response=response)
            error = normalize_provider_error(exc)
            self.assertEqual((error.code, error.retryable, error.retry_after_seconds), (code, retryable, 12))
            self.assertFalse(normalize_provider_error(exc, had_delta=True).retryable)

    def test_insufficient_quota_is_not_retried(self):
        response = httpx.Response(429, json={"error": {"code": "insufficient_quota"}}, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        error = normalize_provider_error(httpx.HTTPStatusError("test", request=response.request, response=response))
        self.assertFalse(error.retryable)


class OpenAIAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def test_sync_generation_preserves_context_and_usage(self):
        def handler(request):
            self.assertEqual(request.url.path, "/v1/responses")
            body = json.loads(request.content)
            self.assertEqual(body["input"], [
                {"role": "system", "content": "System instruction"},
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Previous answer"},
                {"role": "user", "content": "Follow up"},
            ])
            self.assertEqual(body["max_output_tokens"], 100)
            self.assertFalse(body["store"])
            self.assertFalse(body["stream"])
            return httpx.Response(200, json=completed())
        with mock_client(handler):
            result = await generate_openai(settings_for(), "gpt-4.1-mini", contents(), "System instruction", 100)
        self.assertEqual((result.text, result.actual_input_tokens, result.output_tokens), ("Hello", 42, 7))

    async def test_exact_token_count_includes_system_and_roles(self):
        def handler(request):
            self.assertEqual(request.url.path, "/v1/responses/input_tokens")
            body = json.loads(request.content)
            self.assertEqual(body["input"][0], {"role": "system", "content": "System"})
            self.assertEqual(body["input"][2]["role"], "assistant")
            return httpx.Response(200, json={"input_tokens": 80})
        with mock_client(handler):
            self.assertEqual(await count_openai_tokens(settings_for(), "gpt-4.1-mini", contents(), "System"), 80)

    async def test_streaming_delivers_deltas_and_final_usage(self):
        events = [
            {"type": "response.output_text.delta", "delta": "Hel"},
            {"type": "response.output_text.delta", "delta": "lo"},
            {"type": "response.completed", "response": completed()},
        ]
        delta = AsyncMock()
        with mock_client(lambda request: httpx.Response(200, text=sse(events), headers={"Content-Type": "text/event-stream"})):
            result = await generate_openai(settings_for(), "gpt-4.1-mini", contents(), "System", 100, delta)
        self.assertEqual([call.args[0] for call in delta.await_args_list], ["Hel", "lo"])
        self.assertEqual((result.text, result.output_tokens), ("Hello", 7))

    async def test_truncated_stream_is_not_accepted_as_success(self):
        events = [{"type": "response.output_text.delta", "delta": "Partial"}]
        with mock_client(lambda request: httpx.Response(200, text=sse(events))), self.assertRaises(LLMError):
            await generate_openai(settings_for(), "gpt-4.1-mini", contents(), "System", 100, AsyncMock())

    async def test_refusal_or_failed_response_does_not_become_empty_success(self):
        for payload in ({"status": "completed", "output": []}, {"status": "failed"}):
            with mock_client(lambda request: httpx.Response(200, json=payload)), self.assertRaises(LLMError):
                await generate_openai(settings_for(), "gpt-4.1-mini", contents(), "System", 100)

    async def test_max_output_truncation_keeps_visible_text(self):
        payload = completed("Partial answer")
        payload.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        with mock_client(lambda request: httpx.Response(200, json=payload)):
            result = await generate_openai(settings_for(), "gpt-4.1-mini", contents(), "System", 100)
        self.assertEqual(result.text, "Partial answer")

    async def test_http_auth_failure_is_preserved_for_gateway(self):
        with mock_client(lambda request: httpx.Response(401, json={"error": {"code": "invalid_api_key"}})):
            with self.assertRaises(httpx.HTTPStatusError) as caught:
                await generate_openai(settings_for(), "gpt-4.1-mini", contents(), "System", 100, AsyncMock())
        self.assertEqual(normalize_provider_error(caught.exception).code, "PROVIDER_AUTH_ERROR")

    async def test_openai_without_optional_quotas_does_not_use_gemini_quota(self):
        reservation = await ModelLimiter().reserve(settings_for(), "gpt-4.1-mini", 200)
        self.assertTrue(reservation.allowed)
        self.assertFalse(reservation.enforced)


class OpenAIGatewayTest(unittest.IsolatedAsyncioTestCase):
    async def test_gateway_uses_openai_and_records_summary_usage(self):
        settings = settings_for(openai_summary_model="summary-model")
        gateway = LLMGateway(uuid4(), exact_count_threshold=0.95)
        gateway.model_limiter.reserve = AsyncMock(return_value=QuotaReservation(True, "", 0, 100, False))
        gateway.model_limiter.reconcile = AsyncMock()
        gateway._write_usage = AsyncMock()
        context = ChatContext("System", contents())
        with patch("app.llm.gateway.runtime_settings", AsyncMock(return_value=settings)), patch("app.llm.gateway.ensure_circuit_closed", AsyncMock(return_value=True)), patch("app.llm.gateway.record_success", AsyncMock()), patch("app.llm.gateway.gemini_client") as gemini, mock_client(lambda request: httpx.Response(200, json=completed())):
            result = await gateway.generate_once(context, operation="summary")
        gemini.assert_not_called()
        self.assertEqual(result.model, "summary-model")
        usage = gateway._write_usage.call_args.kwargs
        self.assertEqual((usage["operation"], usage["actual_input"], usage["output"], usage["status"]), ("summary", 42, 7, "SUCCESS"))

    async def test_gateway_suppresses_retry_after_partial_stream(self):
        gateway = LLMGateway(uuid4(), exact_count_threshold=0.95)
        gateway.model_limiter.reserve = AsyncMock(return_value=QuotaReservation(True, "", 0, 100, False))
        gateway._write_usage = AsyncMock()
        events = [{"type": "response.output_text.delta", "delta": "Partial"}]
        with patch("app.llm.gateway.runtime_settings", AsyncMock(return_value=settings_for())), patch("app.llm.gateway.ensure_circuit_closed", AsyncMock(return_value=True)), mock_client(lambda request: httpx.Response(200, text=sse(events))):
            with self.assertRaises(LLMError) as caught:
                await gateway.generate_once(ChatContext("System", contents()), on_delta=AsyncMock())
        self.assertTrue(caught.exception.had_delta)
        self.assertFalse(caught.exception.retryable)
        self.assertEqual(gateway._write_usage.call_args.kwargs["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
