from __future__ import annotations

from typing import Optional

from app.db.models import Payment, PaymentStatus
from app.db.session import get_sync_db


def exists_by_telegram_charge_id(
    telegram_payment_charge_id: str,
) -> bool:
    """Return True if payment with given telegram charge id exists."""
    db = get_sync_db()
    try:
        exists = (
            db.query(Payment)
            .filter_by(
                telegram_payment_charge_id=telegram_payment_charge_id,
            )
            .one_or_none()
        )
        return exists is not None
    finally:
        db.close()


def create_payment(
    user_id,
    telegram_payment_charge_id: str,
    provider_payment_charge_id: str | None,
    payload: str,
    currency: str,
    amount_stars: int,
    status: PaymentStatus = PaymentStatus.PAID,
    price_stars: int | None = None,
    term_days: int | None = None,
) -> Payment:
    """Persist payment record and return it."""
    db = get_sync_db()
    try:
        payment = Payment(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            provider_payment_charge_id=provider_payment_charge_id,
            payload=payload,
            currency=currency,
            amount_stars=amount_stars,
            status=status,
            price_stars=price_stars,
            term_days=term_days,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment
    finally:
        db.close()


