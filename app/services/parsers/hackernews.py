import requests
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Source, NewsItem
from app.services.extractors.content_extractor import ContentExtractor

settings = get_settings()


class HackerNewsParser:
    def __init__(self, db: Session):
        self.db = db
        self.api = settings.hackernews_api_url
        self.web = settings.hackernews_web_url
        self.content_extractor = ContentExtractor()

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

        ids = requests.get(f"{self.api}/newstories.json").json()[:limit]

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

            item = requests.get(f"{self.api}/item/{sid}.json").json()
            url = item.get("url") or f"{self.web}/item?id={sid}"
            title = item.get("title", "")
            ts = datetime.fromtimestamp(item.get("time", 0))

            # Extract content from web page
            extracted_title, content = self.content_extractor.extract_content(url)
            if not extracted_title:
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