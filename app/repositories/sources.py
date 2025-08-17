from __future__ import annotations

from typing import Iterable, List
from uuid import UUID

from sqlalchemy import select

from app.db.models import Source
from app.db.session import get_sync_db


def list_active_sources(
    
) -> List[Source]:
    """Return all active sources."""
    db = get_sync_db()
    try:
        sources = (
            db.execute(
                select(Source).where(
                    Source.is_active,
                )
            )
            .scalars()
            .all()
        )
        return sources
    finally:
        db.close()


def get_sources_by_ids(
    source_ids: Iterable[UUID],
) -> List[Source]:
    """Return all sources given their IDs."""
    ids_list = [UUID(str(s)) for s in source_ids]
    db = get_sync_db()
    try:
        sources = (
            db.query(Source)
            .filter(
                Source.id.in_(ids_list),
            )
            .all()
        )
        return sources
    finally:
        db.close()


