from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from app.config import get_settings
from app.db.session import get_sync_db
from app.db.models import User, PaymentStatus
from app.repositories import users as users_repo
from app.repositories import payments as payments_repo
from datetime import datetime, timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
from bot.texts import (
    PREMIUM_ACTIVE_TEXT,
    PREMIUM_INACTIVE_TEXT,
    PREMIUM_ALREADY_ACTIVE_TEXT,
    PREMIUM_ALREADY_HAVE_TEXT,
    PREMIUM_UNKNOWN_PRODUCT_TEXT,
    PREMIUM_ACTIVATED_TEXT,
    PREMIUM_ALREADY_ACTIVATED_TEXT,
)


router = Router()
@router.message(F.text == "/premium")
async def premium_status(
    message: Message,
) -> None:
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(message.from_user.id)).one_or_none()
        has_premium = users_repo.has_active_premium(
            telegram_id=str(message.from_user.id),
        )
        if has_premium and user and user.premium_until:
            await message.answer(
                text=PREMIUM_ACTIVE_TEXT.format(
                    until=user.premium_until,
                ),
            )
            return
        
        await message.answer_invoice(
            title=PREMIUM_TITLE,
            description=PREMIUM_DESCRIPTION,
            payload=PREMIUM_PAYLOAD,
            provider_token="",
            currency=PREMIUM_CURRENCY,
            prices=[
                LabeledPrice(
                    label="Premium (1 month)",
                    amount=settings.premium_price_stars or PREMIUM_PRICE_STARS,
                ),
            ],
        )
    finally:
        db.close()


PREMIUM_TITLE: str = "⭐ Premium"
PREMIUM_DESCRIPTION: str = (
    "Unlock multiple sources for 1 month."
)
PREMIUM_PAYLOAD: str = "premium_unlimited_sources"
PREMIUM_CURRENCY: str = "XTR"
settings = get_settings()
PREMIUM_PRICE_STARS: int = 1


@router.callback_query(lambda c: c.data == "open_premium")
async def open_premium(
    cb: CallbackQuery,
) -> None:
    """Open invoice for Premium using Telegram Stars (XTR)."""
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
        has_premium = users_repo.has_active_premium(
            telegram_id=str(cb.from_user.id),
        )
    finally:
        db.close()
    if has_premium:
        await cb.message.answer(
            text=PREMIUM_ALREADY_ACTIVE_TEXT,
        )
        await cb.answer()
        return
    await cb.message.answer_invoice(
        title=PREMIUM_TITLE,
        description=PREMIUM_DESCRIPTION,
        payload=PREMIUM_PAYLOAD,
        provider_token="",
        currency=PREMIUM_CURRENCY,
        prices=[
            LabeledPrice(
                label="Premium (1 month)",
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
        db = get_sync_db()
        try:
            user = (
                db.query(User)
                .filter_by(
                    telegram_id=str(query.from_user.id),
                )
                .one_or_none()
            )
            has_premium = users_repo.has_active_premium(
                telegram_id=str(query.from_user.id),
            )
        finally:
            db.close()
        if has_premium:
            await query.answer(
                ok=False,
                error_message=PREMIUM_ALREADY_HAVE_TEXT,
            )
            return
        await query.answer(
            ok=True,
        )
        return
    await query.answer(
        ok=False,
        error_message=PREMIUM_UNKNOWN_PRODUCT_TEXT,
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

        if payments_repo.exists_by_telegram_charge_id(
            telegram_payment_charge_id=sp.telegram_payment_charge_id,
        ):
            await message.answer(
                text=PREMIUM_ALREADY_ACTIVATED_TEXT,
            )
            db.close()
            return

        payments_repo.create_payment(
            user_id=user.id,
            telegram_payment_charge_id=sp.telegram_payment_charge_id,
            provider_payment_charge_id=sp.provider_payment_charge_id,
            payload=sp.invoice_payload,
            currency=sp.currency,
            amount_stars=sp.total_amount,
            status=PaymentStatus.PAID,
            price_stars=sp.total_amount,
            term_days=None if settings.premium_is_lifetime else settings.premium_term_days,
        )

        now = datetime.utcnow()
        current_until = user.premium_until or now
        if settings.premium_is_lifetime:
            user.premium_until = max(current_until, now) + timedelta(days=365 * 100)
        else:
            term_days = settings.premium_term_days
            user.premium_until = max(current_until, now) + timedelta(days=term_days)
        db.commit()
    finally:
        db.close()

    logging.getLogger(__name__).info(
        "premium_activated",
        extra={
            "telegram_payment_charge_id": sp.telegram_payment_charge_id,
            "total_amount": sp.total_amount,
            "user_id": user_id_telegram,
        },
    )

    kb = InlineKeyboardBuilder()
    kb.button(
        text="📰 Back to sources",
        callback_data="back_to_selection",
    )
    kb.adjust(1)
    await message.answer(
        text=PREMIUM_ACTIVATED_TEXT,
        reply_markup=kb.as_markup(),
    )


