from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import get_settings
from app.services.llm.openai_client import (
    OpenAIChatClient,
    build_messages,
)


SYSTEM_PROMPT: str = (
    "You are a world-class technology news editor. "
    "Write a concise TL;DR in English as 3–5 short bullet points. "
    "Be factual and specific (who/what/when/why/impact). "
    "No marketing fluff, no speculation. "
    "Total length under 600 characters. "
    "Output only bullet points starting with '• '."
)


@dataclass
class SummarizeInput:
    """Input payload for summarization."""

    title: str
    content: str
    url: Optional[str]


class SummarizerAgent:
    """Abstractive TL;DR generator with opinionated, deterministic style."""

    def __init__(
        self,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self.client = OpenAIChatClient(
            model=(model or settings.openai_model or "gpt-4o-mini"),
            request_timeout_seconds=20,
            max_retries=2,
        )

    def summarize(
        self,
        payload: SummarizeInput,
        max_output_tokens: int = 512,
        temperature: float = 0.1,
        seed: int | None = 42,
    ) -> str:
        """Generate a concise TL;DR for the given article content."""
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
            parts.append(f"Title: {title}")
        if content:
            parts.append("Article:\n" + content)
        if url:
            parts.append(f"Source: {url}")
        return "\n\n".join(parts)

    def _postprocess(
        self,
        text: str,
    ) -> str:
        cleaned = (text or "").strip()
        # Ensure bullets start with '• '
        lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
        bullets = []
        for line in lines:
            if line.startswith("•"):
                bullets.append(line if line.startswith("• ") else ("• " + line.lstrip("• ").strip()))
            elif line.startswith("-") or line.startswith("*"):
                bullets.append("• " + line.lstrip("-* ").strip())
            else:
                bullets.append("• " + line)
        result = "\n".join(bullets[:5])
        if len(result) > 700:
            result = result[:700].rstrip()
        return result


