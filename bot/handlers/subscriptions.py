from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from uuid import UUID

from app.db.models import User, Subscription, Language, Source
from app.db.session import get_sync_db
from bot.state import get_selection, pop_selection
from bot.texts import SUBSCRIPTION_CREATED_TEXT, SUBSCRIPTION_UPDATED_TEXT

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

        first_source_id = next(iter(sel)) if sel else None
        first_source = (
            db.query(Source)
            .filter(
                Source.id == str(first_source_id),
            )
            .first()
            if first_source_id
            else None
        )
        if not first_source:
            current_sub = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == user.id,
                    Subscription.is_active == True,
                )
                .first()
            )
            if current_sub:
                first_source = db.query(Source).filter(Source.id == str(current_sub.source_id)).first()
                first_source_id = current_sub.source_id
        sources_text = f"📰 <b>{first_source.name}</b>" if first_source else "Unknown source"

        language = db.query(Language).filter(Language.code == code).first()
        language_name = language.name if language else code
        flag_emoji = get_flag_emoji(code)

        existing_subs = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
            )
            .all()
        )
        
        target_sub = None
        if existing_subs:
            target_sub = existing_subs[0]
            if first_source_id is not None:
                target_sub.source_id = first_source_id
            target_sub.language = code
        else:
            if first_source_id is None:
                await cb.answer("⚠️ Please select a source first", show_alert=True)
                return
            target_sub = Subscription(
                user_id=user.id,
                source_id=first_source_id,
                language=code,
                is_active=True,
            )
            db.add(target_sub)
        db.commit()

        pop_selection(chat)
        
    finally:
        db.close()

    kb = InlineKeyboardBuilder()
    kb.button(
        text="⚙️ /settings",
        callback_data="cmd_settings",
    )
    kb.adjust(1)
    
    text_tpl = SUBSCRIPTION_UPDATED_TEXT if existing_subs else SUBSCRIPTION_CREATED_TEXT
    await cb.message.edit_text(
        text=text_tpl.format(
            source=sources_text,
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
