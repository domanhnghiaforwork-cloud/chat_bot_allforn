"""OpenAI Responses API adapter; retry do application quản lý."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.config.settings import Settings
from app.llm.errors import LLMError
from app.llm.generation import GenerationResult


def openai_input(contents, system_instruction: str | None = None) -> list[dict[str, str]]:
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    if isinstance(contents, str):
        messages.append({"role": "user", "content": contents})
    else:
        for content in contents:
            messages.append({
                "role": "assistant" if content.role == "model" else "user",
                "content": "\n".join(part.text or "" for part in (content.parts or [])),
            })
    return messages


def openai_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://api.openai.com/v1/",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        timeout=settings.openai_request_timeout_seconds,
    )


async def count_openai_tokens(settings: Settings, model: str, contents, system_instruction: str | None) -> int:
    async with openai_client(settings) as client:
        response = await client.post("responses/input_tokens", json={
            "model": model, "input": openai_input(contents, system_instruction),
        })
        response.raise_for_status()
        return int(response.json()["input_tokens"])


def _result(response: dict[str, Any], model: str) -> GenerationResult:
    status = response.get("status")
    if status not in {"completed", "incomplete"}:
        raise LLMError("PROVIDER_UNAVAILABLE", "OpenAI không hoàn tất phản hồi", retryable=True)
    if status == "incomplete" and response.get("incomplete_details", {}).get("reason") != "max_output_tokens":
        raise LLMError("SAFETY_BLOCKED", "OpenAI không trả về nội dung đầy đủ")
    text = "".join(
        part.get("text", "")
        for item in response.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    )
    if not text:
        raise LLMError("SAFETY_BLOCKED", "OpenAI không trả về nội dung; kiểm tra ngân sách token đầu ra")
    usage = response.get("usage") or {}
    return GenerationResult(text, model, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))


async def generate_openai(
    settings: Settings,
    model: str,
    contents,
    system_instruction: str,
    max_output_tokens: int,
    on_delta: Callable[[str], Awaitable[None]] | None = None,
) -> GenerationResult:
    payload = {
        "model": model,
        "input": openai_input(contents, system_instruction),
        "max_output_tokens": max_output_tokens,
        "store": False,
        "stream": on_delta is not None,
    }
    async with openai_client(settings) as client:
        if on_delta is None:
            response = await client.post("responses", json=payload)
            response.raise_for_status()
            return _result(response.json(), model)
        final = None
        async with client.stream("POST", "responses", json=payload) as response:
            if response.is_error:
                await response.aread()
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                event = json.loads(data)
                kind = event.get("type")
                if kind == "response.output_text.delta" and event.get("delta"):
                    await on_delta(event["delta"])
                elif kind in {"response.completed", "response.incomplete"}:
                    final = event["response"]
                elif kind in {"error", "response.failed"}:
                    raise LLMError("PROVIDER_UNAVAILABLE", "OpenAI không hoàn tất phản hồi", retryable=True)
        if final is None:
            raise LLMError("PROVIDER_UNAVAILABLE", "Kết nối OpenAI bị ngắt trước khi hoàn tất", retryable=True)
        return _result(final, model)
