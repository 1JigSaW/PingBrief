from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import get_settings
from app.services.llm.open_ai.service import (
    OpenAIChatService,
    build_messages,
)
from app.services.agents.summarizer.prompt import SYSTEM_PROMPT


@dataclass
class SummarizeInput:
    """Input payload for summarization."""

    title: str
    content: str
    url: Optional[str]


class SummarizerAgent:
    """Abstractive TL;DR generator with deterministic style."""

    def __init__(
        self,
        model: str | None = None,
        request_timeout_seconds: int = 20,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()
        self.client = OpenAIChatService(
            model=(model or settings.openai_model or "gpt-4o-mini"),
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
        )

    def summarize(
        self,
        payload: SummarizeInput,
        max_output_tokens: int = 512,
        temperature: float = 0.1,
        seed: int | None = 42,
    ) -> str:
        article = self._compose_article(
            title=payload.title,
            content=payload.content,
            url=payload.url,
        )
        messages = build_messages(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=article,
        )
        text = self.client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_output_tokens,
            seed=seed,
        )
        return self._postprocess(
            text=text,
        )

    def _compose_article(
        self,
        title: str,
        content: str,
        url: Optional[str],
    ) -> str:
        parts: list[str] = []
        if title:
            parts.append(
                f"Title: {title}",
            )
        if content:
            parts.append(
                "Article:\n" + content,
            )
        if url:
            parts.append(
                f"Source: {url}",
            )
        return "\n\n".join(parts)

    def _postprocess(
        self,
        text: str,
    ) -> str:
        cleaned = (text or "").strip()
        lines = [
            l.strip().lstrip("•-*").lstrip().lstrip("0123456789. ")
            for l in cleaned.splitlines()
            if l.strip()
        ]
        result = "\n".join(lines[:5])
        if len(result) > 700:
            result = result[:700].rstrip()
        return result


