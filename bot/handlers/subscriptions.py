from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from uuid import UUID

from app.db.models import User, Subscription, Language, Source
from app.db.session import get_sync_db
from app.repositories import languages as languages_repo
from app.repositories import subscriptions as subscriptions_repo
from app.repositories import sources as sources_repo
from app.repositories import users as users_repo
from bot.utils.flags import get_flag_emoji
from bot.state import get_selection, pop_selection
from datetime import datetime
from bot.texts import (
    SUBSCRIPTION_CREATED_TEXT,
    SUBSCRIPTION_UPDATED_TEXT,
    PAYWALL_MULTIPLE_SOURCES_TEXT,
    LOADING_SAVING_PREFS_TEXT,
)
from bot.keyboards.builders import build_paywall_keyboard

router = Router()

TOP_LANGUAGES = [
    "en",
    "ru",
    "es",
    "fr",
    "de",
    "zh",
    "ja",
    "ko",
    "it",
    "pt",
    "ar",
    "hi",
    "tr",
    "nl",
    "sv",
]

async def build_languages_kb():
    langs = languages_repo.list_by_codes(
        codes=TOP_LANGUAGES,
    )
    kb = InlineKeyboardBuilder()
    for lang in langs:
        flag_emoji = get_flag_emoji(
            language_code=lang.code,
        )
        kb.button(
            text=f"{flag_emoji} {lang.name}",
            callback_data=f"lang:{lang.code}",
        )
    kb.adjust(2)
    return kb.as_markup()

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def language_chosen(cb: CallbackQuery):
    code = cb.data.split(
        ":",
        1,
    )[1]
    chat = cb.from_user.id
    sel = get_selection(chat)
    await cb.answer()
    try:
        await cb.message.edit_text(
            text=LOADING_SAVING_PREFS_TEXT,
        )
    except Exception:
        pass

    db = get_sync_db()
    try:
        user = users_repo.ensure_user(
            telegram_id=str(cb.from_user.id),
            username=cb.from_user.username,
            first_name=cb.from_user.first_name,
            last_name=cb.from_user.last_name,
        )

        language = languages_repo.get_by_code(
            code=code,
        )
        language_name = language.name if language else code
        flag_emoji = get_flag_emoji(
            language_code=code,
        )

        all_subs = subscriptions_repo.list_by_user_id(
            user_id=user.id,
        )
        had_active_before = any(
            sub.is_active for sub in all_subs
        )

        selected_source_ids = set(sel)

        if selected_source_ids and len(selected_source_ids) > 1:
            has_premium = users_repo.has_active_premium(
                telegram_id=str(cb.from_user.id),
            )
            if not has_premium:
                await cb.message.answer(
                    text=PAYWALL_MULTIPLE_SOURCES_TEXT,
                    reply_markup=build_paywall_keyboard().as_markup(),
                )
                await cb.answer()
                return

        if selected_source_ids:
            subscriptions_repo.upsert_for_user_and_sources_with_language(
                user_id=user.id,
                source_ids=selected_source_ids,
                language_code=code,
            )
        else:
            subscriptions_repo.set_language_for_all_user_subscriptions(
                user_id=user.id,
                language_code=code,
            )

        if selected_source_ids:
            selected_sources = sources_repo.get_sources_by_ids(
                source_ids=list(selected_source_ids),
            )
        else:
            selected_sources = [sub.source for sub in all_subs if sub.is_active]

        sources_text = "\n".join([f"📰 <b>{src.name}</b>" for src in selected_sources]) if selected_sources else "Unknown source(s)"

        pop_selection(chat)

        # Determine whether this was the first-time creation
        all_subs_after = subscriptions_repo.list_by_user_id(
            user_id=user.id,
        )
        has_active_after = any(
            sub.is_active for sub in all_subs_after
        )

    finally:
        db.close()

    kb = InlineKeyboardBuilder()
    kb.button(
        text="⚙️ /settings",
        callback_data="cmd_settings",
    )
    kb.adjust(1)
    
    text_tpl = SUBSCRIPTION_UPDATED_TEXT if had_active_before else SUBSCRIPTION_CREATED_TEXT
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
