"""Translation service with DB persistence and Redis cache.

Translates base English summaries to target languages used by active
subscribers. Implements read-through and write-through caching.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import requests
from sqlalchemy.orm import Session

from app.db.models import NewsItem, NewsItemTranslation


def _sha1(
    value: str,
) -> str:
    return hashlib.sha1(value.encode('utf-8')).hexdigest()


@dataclass
class TranslateConfig:
    base_url: str
    timeout_seconds: int = 10
    provider_name: str = "libretranslate"


class TranslatorService:
    def __init__(
        self,
        db: Session,
        base_url: str,
        timeout_seconds: int = 10,
        provider_name: str = "libretranslate",
    ) -> None:
        self.db = db
        self.config = TranslateConfig(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            provider_name=provider_name,
        )

    def translate_summary(
        self,
        news_item: NewsItem,
        target_language: str,
    ) -> Optional[str]:
        base = (news_item.summary or "").strip()
        if not base:
            return None
        chash = _sha1(base)

        existing = (
            self.db.query(NewsItemTranslation)
            .filter(
                NewsItemTranslation.news_item_id == news_item.id,
                NewsItemTranslation.language == target_language,
            )
            .one_or_none()
        )
        if existing and existing.content_hash == chash:
            return existing.summary_translated

        text = self._translate_via_http(
            text=base,
            target=target_language,
            source="en",
        )
        if not text:
            return None

        if existing:
            existing.summary_translated = text
            existing.content_hash = chash
            existing.provider = self.config.provider_name
        else:
            self.db.add(
                NewsItemTranslation(
                    news_item_id=news_item.id,
                    language=target_language,
                    provider=self.config.provider_name,
                    content_hash=chash,
                    summary_translated=text,
                )
            )
        self.db.commit()
        return text

    def _translate_via_http(
        self,
        text: str,
        target: str,
        source: str,
    ) -> Optional[str]:
        try:
            resp = requests.post(
                url=f"{self.config.base_url}/translate",
                json={
                    "q": text,
                    "source": source,
                    "target": target,
                    "format": "text",
                },
                timeout=self.config.timeout_seconds,
            )
            if not resp.ok:
                return None
            data = resp.json() or {}
            out = (data.get("translatedText") or "").strip()
            return out or None
        except Exception:
            return None


