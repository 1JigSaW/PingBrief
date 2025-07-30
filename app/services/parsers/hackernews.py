import requests
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Source, Subscription, Digest, DigestStatus

settings = get_settings()


class HackerNewsParser:
    def __init__(self, db: Session):
        self.db = db
        self.api = str(settings.hackernews_api_url)
        self.web = str(settings.hackernews_web_url)

    def save_new_sync(self, limit: int = 50):
        source = self.db.query(Source).filter_by(name="Hacker News").one_or_none()
        if source is None:
            source = Source(
                name="Hacker News",
                url=self.web,
                default_language="en",
                is_active=True,
            )
            self.db.add(source)
            self.db.commit()

        subs = (
            self.db.execute(
                select(Subscription).where(
                    Subscription.source_id == source.id,
                    Subscription.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )
        if not subs:
            return

        ids = requests.get(f"{self.api}/newstories.json").json()[:limit]
        for sid in ids:
            item = requests.get(f"{self.api}/item/{sid}.json").json()
            url = item.get("url") or f"{self.web}/item?id={sid}"
            title = item.get("title", "")
            ts = datetime.fromtimestamp(item.get("time", 0))

            for sub in subs:
                exists = self.db.execute(
                    select(Digest).where(
                        Digest.subscription_id == sub.id,
                        Digest.url == url,
                    )
                ).first()
                if exists:
                    continue

                d = Digest(
                    user_id=sub.user_id,
                    subscription_id=sub.id,
                    title=title,
                    summary="",
                    url=url,
                    scheduled_for=ts,
                    status=DigestStatus.PENDING,
                )
                self.db.add(d)

        self.db.commit()
