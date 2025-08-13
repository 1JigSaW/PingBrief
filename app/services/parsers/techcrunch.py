"""TechCrunch RSS parser that stores new items into the database.

Strategy:
- Read RSS (https://techcrunch.com/feed/)
- Prefer GUID as stable external_id, fallback to link
- Try to extract full text from content:encoded; otherwise fetch page and extract
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional, Tuple

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
from lxml import html as lh
from urllib.parse import urlparse, parse_qs

from app.db.models import NewsItem, Source
from app.services.extractors.full_text_rss_client import FullTextRssClient


class TechCrunchParser:
    def __init__(
        self,
        db: Session,
        feed_url: str = "https://techcrunch.com/feed/",
    ) -> None:
        self.db = db
        self.feed_url = feed_url
        self.http_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.ftr = FullTextRssClient()

    def save_new_sync(
        self,
        limit: int = 50,
    ) -> None:
        source = self._ensure_source()
        items = self._fetch_rss_items(
            feed_url=self.feed_url,
            limit=limit,
        )

        for item in items:
            external_id = item.get("guid") or item.get("link")
            if not external_id:
                continue

            existing_item = self.db.scalar(
                select(NewsItem).where(
                    NewsItem.external_id == external_id,
                    NewsItem.source_id == source.id,  # type: ignore[arg-type]
                )
            )

            title = item.get("title") or ""
            link = item.get("link") or external_id or ""
            published_at = self._parse_pub_date(
                pub_date=item.get("pubDate"),
            )

            if existing_item and (not existing_item.content or len(str(existing_item.content).strip()) == 0):
                content = self.ftr.extract(link) if link else None
                if not content:
                    extracted_title, content = self._extract_via_wp_api(
                        link=link,
                        guid=item.get("guid"),
                    )
                if not content:
                    rt, rc = self._extract_via_wp_api_raw_html(link=link)
                    if rc:
                        content = rc
                        if not extracted_title and rt:
                            extracted_title = self._html_to_text(rt)
                if not content:
                    desc = item.get("description")
                    if desc:
                        try:
                            doc = lh.fromstring(desc)
                            text = doc.text_content().strip()
                            content = " ".join(text.split()) if text else None
                        except Exception:
                            pass
                if not content:
                    content = f"{title}\n{link}" if title or link else None
                if content:
                    existing_item.content = content
                    if extracted_title and not (existing_item.title and len(existing_item.title.strip()) > 0):
                        existing_item.title = extracted_title
                    self.db.commit()
                continue

            if existing_item:
                continue

            content = self.ftr.extract(link) if link else None
            extracted_title, wp_content = self._extract_via_wp_api(
                link=link,
                guid=item.get("guid"),
            )
            if not content and wp_content:
                content = wp_content

            if not content and link:
                ftr_text = self.ftr.extract(link)
                if ftr_text and len(ftr_text) > 50:
                    content = ftr_text

            if not content:
                raw_title_html, raw_content_html = self._extract_via_wp_api_raw_html(
                    link=link,
                )
                if raw_content_html:
                    content = raw_content_html
                    if not extracted_title and raw_title_html:
                        extracted_title = self._html_to_text(raw_title_html)
            if not content:
                desc = item.get("description")
                if desc:
                    try:
                        doc = lh.fromstring(desc)
                        text = doc.text_content().strip()
                        content = " ".join(text.split()) if text else None
                    except Exception:
                        pass

            final_title = (extracted_title or title or "").strip()
            if not final_title:
                continue

            if not content:
                content = f"{title}\n{link}" if title or link else None

            news_item = NewsItem(
                source_id=source.id,  # type: ignore[arg-type]
                external_id=external_id,
                title=final_title,
                content=(content or None),
                url=link,
                fetched_at=published_at or datetime.utcnow(),
                is_active=True,
            )
            self.db.add(news_item)

        self.db.commit()

    def _extract_via_wp_api(
        self,
        link: str,
        guid: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Use WordPress REST API to fetch full article content.

        - If query has ?p={id} → GET /wp-json/wp/v2/posts/{id}
        - Else try slug: /wp-json/wp/v2/posts?slug={slug}&per_page=1
        Returns (title, plain_text_content) if found, otherwise (None, None).
        """
        try:
            parsed = urlparse(link or "")
            feed_parsed = urlparse(self.feed_url)
            base = f"{parsed.scheme or feed_parsed.scheme}://{parsed.netloc or feed_parsed.netloc}"
            qs = parse_qs((parsed.query or ""))
            post_id_vals = qs.get("p")
            if (not post_id_vals or not post_id_vals[0].isdigit()) and guid:
                try:
                    gparsed = urlparse(guid)
                    gqs = parse_qs(gparsed.query or "")
                    gpid = gqs.get("p", [None])[0]
                    if gpid and str(gpid).isdigit():
                        post_id_vals = [str(gpid)]
                    elif guid.isdigit():
                        post_id_vals = [guid]
                except Exception:
                    pass
            if post_id_vals and post_id_vals[0].isdigit():
                post_id = post_id_vals[0]
                url = f"{base}/wp-json/wp/v2/posts/{post_id}?_fields=title,content"
                resp = requests.get(url, headers=self.http_headers, timeout=15)
                if resp.ok:
                    data = resp.json()
                    title_html = (data.get("title") or {}).get("rendered")
                    content_html = (data.get("content") or {}).get("rendered")
                    title = self._html_to_text(title_html) if title_html else None
                    content = self._html_to_text(content_html) if content_html else None
                    if content:
                        return title, content

            path_parts = [p for p in ((parsed.path or "").split("/")) if p]
            if path_parts:
                slug = path_parts[-1]
                url = f"{base}/wp-json/wp/v2/posts?slug={slug}&_fields=title,content&per_page=1"
                resp = requests.get(url, headers=self.http_headers, timeout=15)
                if resp.ok:
                    arr = resp.json() or []
                    if arr:
                        data = arr[0]
                        title_html = (data.get("title") or {}).get("rendered")
                        content_html = (data.get("content") or {}).get("rendered")
                        title = self._html_to_text(title_html) if title_html else None
                        content = self._html_to_text(content_html) if content_html else None
                        if content:
                            return title, content
        except Exception:
            pass
        return None, None

    def _extract_via_wp_api_raw_html(
        self,
        link: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Fetch raw rendered HTML via WP API (title/content.rendered).

        Returns (title_html, content_html) or (None, None).
        """
        try:
            parsed = urlparse(link)
            base = f"{parsed.scheme}://{parsed.netloc}"
            qs = parse_qs(parsed.query or "")
            post_id_vals = qs.get("p")
            if post_id_vals and post_id_vals[0].isdigit():
                post_id = post_id_vals[0]
                url = f"{base}/wp-json/wp/v2/posts/{post_id}?_fields=title,content"
                resp = requests.get(url, headers=self.http_headers, timeout=15)
                if resp.ok:
                    data = resp.json()
                    title_html = (data.get("title") or {}).get("rendered")
                    content_html = (data.get("content") or {}).get("rendered")
                    if content_html:
                        return title_html, content_html
            path_parts = [p for p in (parsed.path or "").split("/") if p]
            if path_parts:
                slug = path_parts[-1]
                url = f"{base}/wp-json/wp/v2/posts?slug={slug}&_fields=title,content&per_page=1"
                resp = requests.get(url, headers=self.http_headers, timeout=15)
                if resp.ok:
                    arr = resp.json() or []
                    if arr:
                        data = arr[0]
                        title_html = (data.get("title") or {}).get("rendered")
                        content_html = (data.get("content") or {}).get("rendered")
                        if content_html:
                            return title_html, content_html
        except Exception:
            pass
        return None, None

    def _html_to_text(
        self,
        html_fragment: Optional[str],
    ) -> Optional[str]:
        if not html_fragment:
            return None
        try:
            doc = lh.fromstring(html_fragment)
            text = doc.text_content().strip()
            return " ".join(text.split()) if text else None
        except Exception:
            return None

    def _ensure_source(self) -> Source:
        source = self.db.query(Source).filter_by(name="TechCrunch").one_or_none()
        if source is None:
            source = Source(
                name="TechCrunch",
                url=self.feed_url,
                default_language="en",
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
        resp = requests.get(
            url=feed_url,
            headers=self.http_headers,
            timeout=20,
        )
        resp.raise_for_status()
        root = lh.fromstring(resp.content)
        items = []
        for item_el in root.xpath("//item")[:limit]:
            ns = {
                "content": "http://purl.org/rss/1.0/modules/content/",
            }
            item = {
                "title": self._text_or_none(
                    item_el.xpath(
                        "string(title)",
                    ),
                ),
                "link": self._text_or_none(
                    item_el.xpath(
                        "string(link)",
                    ),
                ),
                "guid": self._text_or_none(
                    item_el.xpath(
                        "string(guid)",
                    ),
                ),
                "pubDate": self._text_or_none(
                    item_el.xpath(
                        "string(pubDate)",
                    ),
                ),
                # Try with namespace, then fallback to local-name
                "content_encoded": (
                    self._text_or_none(
                        item_el.xpath(
                            "string(.//content:encoded)",
                            namespaces=ns,
                        ),
                    )
                    or self._text_or_none(
                        item_el.xpath(
                            "string(.//*[local-name() = 'encoded' and namespace-uri() = 'http://purl.org/rss/1.0/modules/content/'])",
                        ),
                    )
                ),
                "description": self._text_or_none(
                    item_el.xpath(
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
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None


    def _parse_pub_date(
        self,
        pub_date: Optional[str],
    ) -> Optional[datetime]:
        if not pub_date:
            return None
        try:
            return parsedate_to_datetime(pub_date)
        except Exception:
            return None

