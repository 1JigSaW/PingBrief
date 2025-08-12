"""User-related database helpers for handlers.

These functions encapsulate session management and common queries.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Subscription, User
from app.db.session import get_sync_db


def get_user_by_telegram_id(
    telegram_id: str,
) -> Optional[User]:
    db = get_sync_db()
    try:
        user = (
            db.query(User)
            .filter_by(telegram_id=telegram_id)
            .one_or_none()
        )
        return user
    finally:
        db.close()


def ensure_user(
    telegram_id: str,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
) -> User:
    db = get_sync_db()
    try:
        user = (
            db.query(User)
            .filter_by(telegram_id=telegram_id)
            .one_or_none()
        )
        if user:
            return user

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def deactivate_all_user_subscriptions(
    user: User,
) -> None:
    db = get_sync_db()
    try:
        db.refresh(user)
        for sub in user.subscriptions:
            sub.is_active = False
        db.commit()
    finally:
        db.close()


def list_active_subscriptions(
    user: User,
) -> List[Subscription]:
    db = get_sync_db()
    try:
        db.refresh(user)
        return [sub for sub in user.subscriptions if sub.is_active]
    finally:
        db.close()

