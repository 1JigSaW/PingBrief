from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.state import (
    set_premium,
)
from app.config import get_settings
from app.db.session import get_sync_db
from app.db.models import User, Payment, PaymentStatus
from datetime import datetime, timedelta


router = Router()


# Constants for the Premium product
PREMIUM_TITLE: str = "⭐ Premium"
PREMIUM_DESCRIPTION: str = (
    "Unlock multiple sources and advanced features."
)
PREMIUM_PAYLOAD: str = "premium_unlimited_sources"
PREMIUM_CURRENCY: str = "XTR"  # Telegram Stars
# Amount is in the smallest units. For Stars, use integer stars (1 star = 1 unit)
settings = get_settings()
PREMIUM_PRICE_STARS: int = 1  # overridden by settings if provided


@router.callback_query(lambda c: c.data == "open_premium")
async def open_premium(
    cb: CallbackQuery,
) -> None:
    """Open invoice for Premium using Telegram Stars (XTR)."""
    await cb.message.answer_invoice(
        title=PREMIUM_TITLE,
        description=PREMIUM_DESCRIPTION,
        payload=PREMIUM_PAYLOAD,
        provider_token="",
        currency=PREMIUM_CURRENCY,
        prices=[
            LabeledPrice(
                label="Premium access",
                amount=settings.premium_price_stars or PREMIUM_PRICE_STARS,
            ),
        ],
    )
    await cb.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(
    query: PreCheckoutQuery,
) -> None:
    """Confirm checkout for Premium invoices."""
    if query.invoice_payload == PREMIUM_PAYLOAD:
        await query.answer(
            ok=True,
        )
        return
    await query.answer(
        ok=False,
        error_message="Unknown product",
    )


@router.message(F.successful_payment)
async def successful_payment_handler(
    message: Message,
) -> None:
    """Grant Premium after successful payment."""
    sp = message.successful_payment
    if not sp:
        return
    if sp.invoice_payload != PREMIUM_PAYLOAD:
        return

    user_id_telegram = message.from_user.id if message.from_user else None
    if not user_id_telegram:
        return

    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(user_id_telegram)).one_or_none()
        if not user:
            user = User(
                telegram_id=str(user_id_telegram),
                username=message.from_user.username if message.from_user else None,
                first_name=message.from_user.first_name if message.from_user else None,
                last_name=message.from_user.last_name if message.from_user else None,
            )
            db.add(user)
            db.flush()

        # Idempotency: check charge id
        exists = (
            db.query(Payment)
            .filter_by(
                telegram_payment_charge_id=sp.telegram_payment_charge_id,
            )
            .one_or_none()
        )
        if exists:
            await message.answer("✅ Premium is already activated.")
            db.close()
            return

        # Record payment
        payment = Payment(
            user_id=user.id,
            telegram_payment_charge_id=sp.telegram_payment_charge_id,
            provider_payment_charge_id=sp.provider_payment_charge_id,
            payload=sp.invoice_payload,
            currency=sp.currency,
            amount_stars=sp.total_amount,
            status=PaymentStatus.PAID,
        )
        db.add(payment)

        # Extend premium_until (lifetime or fixed term)
        now = datetime.utcnow()
        current_until = user.premium_until or now
        if settings.premium_is_lifetime:
            # Far future date to represent lifetime (e.g., +100 years)
            user.premium_until = max(current_until, now) + timedelta(days=365 * 100)
        else:
            term_days = settings.premium_term_days
            user.premium_until = max(current_until, now) + timedelta(days=term_days)
        db.commit()
    finally:
        db.close()

    # Volatile cache for current process (optional)
    set_premium(
        user_id=user_id_telegram,
    )

    await message.answer("✅ Premium activated. You can now use multiple sources.")


