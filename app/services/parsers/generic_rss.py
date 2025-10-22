from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional, Tuple

import requests
from lxml import html as lh
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import NewsItem, Source
from app.services.extractors.full_text_rss_client import FullTextRssClient


class GenericRssParser:
    """Generic RSS parser that stores new items into the database.

    The parser tries, in order:
    1. content:encoded from RSS
    2. description text content
    3. FullTextRssClient extraction by article link
    """

    def __init__(
        self,
        db: Session,
        source_name: str,
        feed_url: str,
        default_language: str = "en",
    ) -> None:
        self.db = db
        self.source_name = source_name
        self.feed_url = feed_url
        self.default_language = default_language
        self.http_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.ftr = FullTextRssClient()

    def save_new_sync(
        self,
        limit: int = 50,
    ) -> None:
        """Fetch RSS items and persist new or incomplete ones."""
        source = self._ensure_source()
        items = self._fetch_rss_items(
            feed_url=self.feed_url,
            limit=limit,
        )

        for item in items:
            external_id = (
                item.get("guid")
                or item.get("link")
            )
            if not external_id:
                continue

            existing_item: Optional[NewsItem] = self.db.scalar(
                select(NewsItem).where(
                    NewsItem.external_id == external_id,
                    NewsItem.source_id == source.id,
                )
            )

            title = item.get("title") or ""
            link = item.get("link") or external_id or ""
            published_at = self._parse_pub_date(
                pub_date=item.get("pubDate"),
            )

            content_encoded = item.get("content_encoded")
            description_text = self._html_to_text(
                html_fragment=item.get("description"),
            )

            content: Optional[str] = None
            if content_encoded and len(content_encoded.strip()) > 0:
                content = self._html_to_text(
                    html_fragment=content_encoded,
                )
            if not content and description_text:
                content = description_text
            if not content and link:
                extracted = self.ftr.extract(
                    url=link,
                )
                if extracted and len(extracted.strip()) > 0:
                    content = extracted

            if existing_item:
                if not existing_item.content and content:
                    existing_item.content = content
                    if title and (not existing_item.title or len(existing_item.title.strip()) == 0):
                        existing_item.title = title
                    self.db.commit()
                continue

            final_title = (title or "").strip()
            if not final_title:
                continue

            if not content:
                content = f"{title}\n{link}" if (title or link) else None

            news_item = NewsItem(
                source_id=source.id,
                external_id=external_id,
                title=final_title,
                content=(content or None),
                url=link,
                fetched_at=published_at or datetime.utcnow(),
                is_active=True,
            )
            self.db.add(news_item)

        self.db.commit()

    def _ensure_source(
        self,
    ) -> Source:
        """Get or create `Source` row for the current feed."""
        source = self.db.query(Source).filter_by(name=self.source_name).one_or_none()
        if source is None:
            source = Source(
                name=self.source_name,
                url=self.feed_url,
                default_language=self.default_language,
                is_active=True,
            )
            self.db.add(source)
            self.db.commit()
        return source

    def _fetch_rss_items(
        self,
        feed_url: str,
        limit: int,
    ) -> list[dict]:
        """Download and parse RSS XML and return a list of items."""
        resp = requests.get(
            url=feed_url,
            headers=self.http_headers,
            timeout=20,
        )
        resp.raise_for_status()
        root = lh.fromstring(resp.content)
        items: list[dict] = []
        for item_el in root.xpath("//item")[:limit]:
            ns = {
                "content": "http://purl.org/rss/1.0/modules/content/",
            }
            item = {
                "title": self._text_or_none(
                    value=item_el.xpath(
                        "string(title)",
                    ),
                ),
                "link": self._text_or_none(
                    value=item_el.xpath(
                        "string(link)",
                    ),
                ),
                "guid": self._text_or_none(
                    value=item_el.xpath(
                        "string(guid)",
                    ),
                ),
                "pubDate": self._text_or_none(
                    value=item_el.xpath(
                        "string(pubDate)",
                    ),
                ),
                "content_encoded": (
                    self._text_or_none(
                        value=item_el.xpath(
                            "string(.//content:encoded)",
                            namespaces=ns,
                        ),
                    )
                    or self._text_or_none(
                        value=item_el.xpath(
                            "string(.//*[local-name() = 'encoded' and namespace-uri() = 'http://purl.org/rss/1.0/modules/content/'])",
                        ),
                    )
                ),
                "description": self._text_or_none(
                    value=item_el.xpath(
                        "string(description)",
                    ),
                ),
            }
            items.append(item)
        return items

    def _text_or_none(
        self,
        value: object,
    ) -> Optional[str]:
        """Convert any value to a stripped string or None."""
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    def _parse_pub_date(
        self,
        pub_date: Optional[str],
    ) -> Optional[datetime]:
        """Parse RFC 2822 pubDate into datetime or return None."""
        if not pub_date:
            return None
        try:
            return parsedate_to_datetime(pub_date)
        except Exception:
            return None

    def _html_to_text(
        self,
        html_fragment: Optional[str],
    ) -> Optional[str]:
        """Convert small HTML fragments to plain text."""
        if not html_fragment:
            return None
        try:
            doc = lh.fromstring(html_fragment)
            text = doc.text_content().strip()
            return " ".join(text.split()) if text else None
        except Exception:
            return None


