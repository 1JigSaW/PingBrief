"""Thin OpenAI chat client wrapper (service layer)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import openai

from app.config import get_settings


@dataclass
class ChatMessage:
    role: str
    content: str


class OpenAIChatService:
    def __init__(
        self,
        model: str,
        request_timeout_seconds: int = 20,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set Settings.openai_api_key",
            )
        openai.api_key = settings.openai_api_key
        self.model = model
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max_retries

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.1,
        max_tokens: int = 512,
        seed: int | None = 42,
    ) -> str:
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": m.role, "content": m.content} for m in messages],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_timeout=self.request_timeout_seconds,
                )
                text = ((resp.get("choices") or [{}])[0].get("message", {}).get("content", ""))
                return text or ""
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
        raise RuntimeError(f"OpenAI chat failed after retries: {last_error}")


def build_messages(
    system_prompt: str,
    user_prompt: str,
) -> List[ChatMessage]:
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]


