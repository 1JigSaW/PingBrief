from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Source, NewsItem


async def get_or_create_source(
    db: AsyncSession,
    *,
    name: str,
    url: str,
    is_active: bool,
) -> Source:
    q = select(Source).where(Source.name == name)
    result = await db.execute(q)
    source = result.scalar_one_or_none()
    if source:
        return source
    source = Source(name=name, url=url, is_active=is_active)
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source

async def get_or_create_news_item(db: AsyncSession, **kwargs) -> NewsItem:
    q = await db.execute(select(NewsItem).filter_by(**kwargs))
    obj = q.scalars().first()
    if obj:
        return obj
    obj = NewsItem(**kwargs)
    db.add(obj)
    await db.commit()
    return obj

async def list_recent_news(db: AsyncSession, limit: int = 100):
    q = await db.execute(
        select(NewsItem)
        .order_by(NewsItem.published_at.desc())
        .limit(limit)
    )
    return q.scalars().all()
