from __future__ import annotations

from typing import Iterable, List, Optional

from app.db.models import Language
from app.db.session import get_sync_db


def get_by_code(
    code: str,
) -> Optional[Language]:
    db = get_sync_db()
    try:
        return (
            db.query(Language)
            .filter(
                Language.code == code,
            )
            .first()
        )
    finally:
        db.close()


def list_by_codes(
    codes: Iterable[str],
) -> List[Language]:
    codes_list = list(codes)
    db = get_sync_db()
    try:
        return (
            db.query(Language)
            .filter(
                Language.code.in_(codes_list),
            )
            .all()
        )
    finally:
        db.close()


