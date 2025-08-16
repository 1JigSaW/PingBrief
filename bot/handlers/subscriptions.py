from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from uuid import UUID

from app.db.models import User, Subscription, Language, Source
from app.db.session import get_sync_db
from bot.state import get_selection, pop_selection
from datetime import datetime
from bot.texts import SUBSCRIPTION_CREATED_TEXT, SUBSCRIPTION_UPDATED_TEXT, PAYWALL_MULTIPLE_SOURCES_TEXT
from bot.keyboards.builders import build_paywall_keyboard

router = Router()

TOP_LANGUAGES = [
    "en",  # English
    "ru",  # Russian
    "es",  # Spanish
    "fr",  # French
    "de",  # German
    "zh",  # Chinese
    "ja",  # Japanese
    "ko",  # Korean
    "it",  # Italian
    "pt",  # Portuguese
    "ar",  # Arabic
    "hi",  # Hindi
    "tr",  # Turkish
    "nl",  # Dutch
    "sv",  # Swedish
]

async def build_languages_kb():
    db = get_sync_db()
    try:
        langs = db.query(Language).filter(Language.code.in_(TOP_LANGUAGES)).all()
    finally:
        db.close()
    kb = InlineKeyboardBuilder()
    for lang in langs:
        flag_emoji = get_flag_emoji(lang.code)
        kb.button(text=f"{flag_emoji} {lang.name}", callback_data=f"lang:{lang.code}")
    kb.adjust(2)
    return kb.as_markup()

def get_flag_emoji(lang_code):
    """Get flag emoji for language code"""
    flag_map = {
        "en": "🇺🇸", "ru": "🇷🇺", "es": "🇪🇸", "fr": "🇫🇷", "de": "🇩🇪",
        "zh": "🇨🇳", "ja": "🇯🇵", "ko": "🇰🇷", "it": "🇮🇹", "pt": "🇵🇹",
        "ar": "🇸🇦", "hi": "🇮🇳", "tr": "🇹🇷", "nl": "🇳🇱", "sv": "🇸🇪"
    }
    return flag_map.get(lang_code, "🌍")

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def language_chosen(cb: CallbackQuery):
    code = cb.data.split(
        ":",
        1,
    )[1]
    chat = cb.from_user.id
    sel = get_selection(chat)
    db = get_sync_db()
    try:
        user = (
            db.query(User)
            .filter_by(
                telegram_id=str(cb.from_user.id),
            )
            .one_or_none()
        )
        if not user:
            user = User(telegram_id=str(cb.from_user.id), username=cb.from_user.username)
            db.add(user)
            db.flush()

        language = db.query(Language).filter(Language.code == code).first()
        language_name = language.name if language else code
        flag_emoji = get_flag_emoji(code)

        active_subs = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
            )
            .all()
        )

        selected_source_ids = set(sel)

        # Paywall safety check from DB (persistent premium)
        if selected_source_ids and len(selected_source_ids) > 1:
            has_premium = bool(user and user.premium_until and user.premium_until > datetime.utcnow())
            if not has_premium:
                await cb.message.answer(
                    text=PAYWALL_MULTIPLE_SOURCES_TEXT,
                    reply_markup=build_paywall_keyboard().as_markup(),
                )
                await cb.answer()
                return

        if selected_source_ids:
            existing_by_source = {sub.source_id: sub for sub in active_subs}
            for src_id in selected_source_ids:
                sub = existing_by_source.get(src_id)
                if sub:
                    sub.language = code
                    sub.is_active = True
                else:
                    db.add(
                        Subscription(
                            user_id=user.id,
                            source_id=src_id,
                            language=code,
                            is_active=True,
                        )
                    )
            db.commit()
        else:
            for sub in active_subs:
                sub.language = code
            db.commit()

        if selected_source_ids:
            selected_sources = (
                db.query(Source)
                .filter(Source.id.in_(list(selected_source_ids)))
                .all()
            )
        else:
            selected_sources = [sub.source for sub in active_subs]

        sources_text = "\n".join([f"📰 <b>{src.name}</b>" for src in selected_sources]) if selected_sources else "Unknown source(s)"

        pop_selection(chat)
        
    finally:
        db.close()

    kb = InlineKeyboardBuilder()
    kb.button(
        text="⚙️ /settings",
        callback_data="cmd_settings",
    )
    kb.adjust(1)
    
    had_subscriptions = False
    try:
        db = get_sync_db()
        u = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
        if u and u.subscriptions:
            had_subscriptions = any(s.is_active for s in u.subscriptions)
    finally:
        db.close()
    text_tpl = SUBSCRIPTION_UPDATED_TEXT if had_subscriptions else SUBSCRIPTION_CREATED_TEXT
    await cb.message.edit_text(
        text=text_tpl.format(
            sources=sources_text,
            flag=flag_emoji,
            language=language_name,
        ),
        reply_markup=kb.as_markup(),
    )
    await cb.answer()

@router.callback_query(lambda c: c.data == "cmd_settings")
async def cmd_settings_button(cb: CallbackQuery):
    from bot.handlers.start import show_settings
    await show_settings(cb.from_user.id, cb.message)
    await cb.answer()
