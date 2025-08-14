import requests
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Source, NewsItem
from app.services.extractors.full_text_rss_client import FullTextRssClient

settings = get_settings()


class HackerNewsParser:
    def __init__(self, db: Session):
        self.db = db
        self.api = settings.hackernews_api_url
        self.web = settings.hackernews_web_url
        self.ftr = FullTextRssClient()

    def save_new_sync(
            self,
            limit: int = 50,
    ):
        source = self.db.query(Source).filter_by(name="Hacker News").one_or_none()
        if source is None:
            source = Source(
                name="Hacker News",
                url=str(self.web),
                default_language="en",
                is_active=True,
            )
            self.db.add(source)
            self.db.commit()

        # Use top stories instead of newstories to get only high-score items
        ids = requests.get(
            url=f"{self.api}/topstories.json",
            timeout=15,
        ).json()[:limit]

        for sid in ids:
            sid_str = str(sid)
            exists = (
                self.db.execute(
                    select(NewsItem).where(
                        NewsItem.external_id == sid_str,
                        NewsItem.source_id == source.id,
                    )
                )
                .first()
            )
            if exists:
                continue

            item = requests.get(
                url=f"{self.api}/item/{sid}.json",
                timeout=15,
            ).json()
            if item.get("type") != "story":
                continue
            url = item.get("url") or f"{self.web}/item?id={sid}"
            title = item.get("title", "")
            ts = datetime.fromtimestamp(item.get("time", 0))

            content = self.ftr.extract(url) or f"{title}\n{url}"
            extracted_title = title

            ni = NewsItem(
                source_id=source.id, # type: ignore
                external_id=sid_str,
                title=extracted_title,
                content=content,
                url=url,
                fetched_at=ts,
                is_active=True,
            )
            self.db.add(ni)

        self.db.commit()