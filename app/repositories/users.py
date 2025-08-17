from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_sync_db


def get_by_telegram_id(
    telegram_id: str,
) -> Optional[User]:
    """Get user by Telegram ID or return None if not exists."""
    db = get_sync_db()
    try:
        user = (
            db.query(User)
            .filter_by(
                telegram_id=telegram_id,
            )
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
    """Return user by Telegram ID or create a new one."""
    db = get_sync_db()
    try:
        user = (
            db.query(User)
            .filter_by(
                telegram_id=telegram_id,
            )
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


def has_active_premium(
    telegram_id: str,
) -> bool:
    """Return True if user has active premium (premium_until > now)."""
    db = get_sync_db()
    try:
        user = (
            db.query(User)
            .filter_by(
                telegram_id=telegram_id,
            )
            .one_or_none()
        )
        if not user or not user.premium_until:
            return False
        return user.premium_until > datetime.utcnow()
    finally:
        db.close()


def grant_or_extend_premium(
    telegram_id: str,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    is_lifetime: bool,
    term_days: int,
) -> datetime:
    """Grant or extend premium for a user and return new expiration timestamp."""
    db = get_sync_db()
    try:
        user = (
            db.query(User)
            .filter_by(
                telegram_id=telegram_id,
            )
            .one_or_none()
        )
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            db.add(user)
            db.flush()

        now = datetime.utcnow()
        current_until = user.premium_until or now
        if is_lifetime:
            user.premium_until = max(current_until, now) + timedelta(days=365 * 100)
        else:
            user.premium_until = max(current_until, now) + timedelta(days=term_days)
        db.commit()
        return user.premium_until
    finally:
        db.close()


