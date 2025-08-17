from __future__ import annotations

from typing import Iterable, List, Optional, Set
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Source, Subscription, User
from app.db.session import get_sync_db


def list_by_user_id(
    user_id: UUID,
) -> List[Subscription]:
    """Return all subscriptions for a given user."""
    db = get_sync_db()
    try:
        subs = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
            )
            .all()
        )
        return subs
    finally:
        db.close()


def list_active_by_user_id(
    user_id: UUID,
) -> List[Subscription]:
    """Return only active subscriptions for a given user."""
    db = get_sync_db()
    try:
        subs = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
            )
            .all()
        )
        return subs
    finally:
        db.close()


def deactivate_all_for_user(
    user_id: UUID,
) -> None:
    """Set all user's subscriptions to inactive."""
    db = get_sync_db()
    try:
        for sub in (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
            )
            .all()
        ):
            sub.is_active = False
        db.commit()
    finally:
        db.close()


def apply_sources_selection(
    user_id: UUID,
    selected_source_ids: Set[UUID],
) -> None:
    """Apply selection of source IDs by activating existing or creating new subscriptions.

    Keeps previous subscriptions but toggles their active state to match the selection.
    New subscriptions are created with language inferred from the first active one, or 'en'.
    """
    db = get_sync_db()
    try:
        all_subs = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
            )
            .all()
        )
        existing_by_source = {sub.source_id: sub for sub in all_subs}

        for sub in all_subs:
            sub.is_active = sub.source_id in selected_source_ids

        ids_to_add = selected_source_ids - set(existing_by_source.keys())
        if ids_to_add:
            preferred_language = None
            for sub in all_subs:
                if sub.is_active:
                    preferred_language = sub.language
                    break
            for src_id in ids_to_add:
                db.add(
                    Subscription(
                        user_id=user_id,
                        source_id=src_id,
                        language=preferred_language or "en",
                        is_active=True,
                    )
                )
        db.commit()
    finally:
        db.close()


def upsert_for_user_and_sources_with_language(
    user_id: UUID,
    source_ids: Iterable[UUID],
    language_code: str,
) -> None:
    """Ensure subscriptions exist for source_ids with a specific language.

    Existing subscriptions will have language updated and be activated.
    Missing subscriptions will be created.
    """
    db = get_sync_db()
    try:
        all_subs = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
            )
            .all()
        )
        existing_by_source = {sub.source_id: sub for sub in all_subs}
        for src_id in source_ids:
            sub = existing_by_source.get(src_id)
            if sub:
                sub.language = language_code
                sub.is_active = True
            else:
                db.add(
                    Subscription(
                        user_id=user_id,
                        source_id=src_id,
                        language=language_code,
                        is_active=True,
                    )
                )
        db.commit()
    finally:
        db.close()


def set_language_for_all_user_subscriptions(
    user_id: UUID,
    language_code: str,
) -> None:
    """Update language for all user's subscriptions."""
    db = get_sync_db()
    try:
        subs = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
            )
            .all()
        )
        for sub in subs:
            sub.language = language_code
        db.commit()
    finally:
        db.close()


def set_first_active_subscription_source(
    user_id: UUID,
    new_source_id: UUID,
) -> None:
    """Change the source of the first active subscription for the user.

    If there is no active subscription, this function does nothing.
    """
    db = get_sync_db()
    try:
        sub = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
            )
            .first()
        )
        if sub:
            sub.source_id = new_source_id
            db.commit()
    finally:
        db.close()


