from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import User, Subscription
from app.db.session import get_sync_db
from app.repositories import users as users_repo
from app.repositories import subscriptions as subscriptions_repo
from app.repositories import sources as sources_repo
from bot.state import get_selection, set_source_selection_context, clear_source_selection_context
from bot.keyboards.builders import (
    build_start_keyboard,
    build_command_shortcuts_keyboard,
    build_settings_keyboard,
    build_go_start_keyboard,
    build_paywall_keyboard_with_keep_options,
)
from bot.texts import (
    WELCOME_NEW_USER_TEXT,
    WELCOME_EXISTING_USER_TEXT,
    UNKNOWN_COMMAND_TEXT,
    NO_SUBSCRIPTIONS_TEXT,
    NO_ACTIVE_SUBSCRIPTIONS_TEXT,
    SETTINGS_HEADER_TEXT,
    PREMIUM_EXPIRED_MULTIPLE_SOURCES_TEXT,
    CHANGE_SOURCES_HEADER_TEXT,
    CHANGE_LANGUAGE_HEADER_TEXT,
)

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    # Ensure user exists
    user = users_repo.ensure_user(
        telegram_id=str(message.from_user.id),
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    # If premium expired and user has >1 active source, show paywall popup once per interaction
    has_premium = users_repo.has_active_premium(
        telegram_id=str(message.from_user.id),
    )
    if not has_premium:
        active_subs_check = subscriptions_repo.list_active_by_user_id(
            user_id=user.id,
        )
        if len(active_subs_check) > 1:
            # Build options with human names
            source_ids = [sub.source_id for sub in active_subs_check]
            srcs = sources_repo.get_sources_by_ids(
                source_ids=source_ids,
            )
            options = [
                (s.name, str(s.id))
                for s in srcs
            ]
            kb_pay = build_paywall_keyboard_with_keep_options(
                options=options,
            )
            await message.answer(
                text=PREMIUM_EXPIRED_MULTIPLE_SOURCES_TEXT,
                reply_markup=kb_pay.as_markup(),
            )
            return

    # Read active subscriptions and render welcome
    active_subs = subscriptions_repo.list_active_by_user_id(
        user_id=user.id,
    )
    if active_subs:
        source_ids = [sub.source_id for sub in active_subs]
        sources = sources_repo.get_sources_by_ids(
            source_ids=source_ids,
        )
        sources_info = [
            f"📰 <b>{src.name}</b>"
            for src in sources
        ]
        if sources_info:
            sources_text = "\n".join(sources_info)
            kb = build_start_keyboard().as_markup()
            await message.answer(
                text=WELCOME_EXISTING_USER_TEXT.format(
                    count=len(active_subs),
                    sources=sources_text,
                ),
                reply_markup=kb,
            )
            return

    sel = get_selection(message.from_user.id)
    sel.clear()
    clear_source_selection_context(message.from_user.id)

    from bot.handlers.sources import build_sources_kb
    kb = await build_sources_kb(
        selected=set(),
    )
    await message.answer(
        text=WELCOME_NEW_USER_TEXT,
        reply_markup=kb,
    )

@router.message(F.text.startswith("/"))
async def unknown_command(message: Message):
    kb = build_command_shortcuts_keyboard(user_id=message.from_user.id).as_markup()
    await message.answer(
        text=UNKNOWN_COMMAND_TEXT,
        reply_markup=kb,
    )

@router.callback_query(lambda c: c.data == "change_source")
async def change_source(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    sel.clear()
    user = users_repo.get_by_telegram_id(
        telegram_id=str(cb.from_user.id),
    )
    if user:
        active_subs = subscriptions_repo.list_active_by_user_id(
            user_id=user.id,
        )
        for sub in active_subs:
            sel.add(sub.source_id)
    set_source_selection_context(chat, "settings")

    from bot.handlers.sources import build_sources_kb
    kb = await build_sources_kb(
        selected=sel,
        context="settings",
    )
    await cb.message.edit_text(
        text=CHANGE_SOURCES_HEADER_TEXT,
        reply_markup=kb,
    )
    await cb.answer()

@router.callback_query(lambda c: c.data == "go_settings")
async def go_to_settings(cb: CallbackQuery):
    await show_settings(cb.from_user.id, cb.message)
    await cb.answer()

@router.callback_query(lambda c: c.data == "cmd_start")
async def cmd_start_button(cb: CallbackQuery):
    await cmd_start(cb.message)
    await cb.answer()

@router.callback_query(lambda c: c.data == "cmd_settings")
async def cmd_settings_button(cb: CallbackQuery):
    await show_settings(cb.from_user.id, cb.message)
    await cb.answer()


async def show_settings(user_id: int, message_or_callback):
    """Render the settings screen for both message and callback contexts."""
    user = users_repo.get_by_telegram_id(
        telegram_id=str(user_id),
    )
    if not user:
        kb = build_go_start_keyboard().as_markup()
        if hasattr(message_or_callback, 'edit_text'):
            await message_or_callback.edit_text(
                text=NO_SUBSCRIPTIONS_TEXT,
                reply_markup=kb,
            )
        else:
            await message_or_callback.answer(
                text=NO_SUBSCRIPTIONS_TEXT,
                reply_markup=kb,
            )
        return

    active_subs = subscriptions_repo.list_active_by_user_id(
        user_id=user.id,
    )
    if not active_subs:
        kb = build_go_start_keyboard().as_markup()
        if hasattr(message_or_callback, 'edit_text'):
            await message_or_callback.edit_text(
                text=NO_ACTIVE_SUBSCRIPTIONS_TEXT,
                reply_markup=kb,
            )
        else:
            await message_or_callback.answer(
                text=NO_ACTIVE_SUBSCRIPTIONS_TEXT,
                reply_markup=kb,
            )
        return

    source_ids = [sub.source_id for sub in active_subs]
    sources = sources_repo.get_sources_by_ids(
        source_ids=source_ids,
    )
    sources_info = [
        f"📰 <b>{src.name}</b>"
        for src in sources
    ]
    sources_text = "\n".join(sources_info)

    kb = build_settings_keyboard(
        user_id=user_id,
    ).as_markup()

    if hasattr(message_or_callback, 'edit_text'):
        await message_or_callback.edit_text(
            text=SETTINGS_HEADER_TEXT.format(
                count=len(active_subs),
                sources=sources_text,
            ),
            reply_markup=kb,
        )
    else:
        await message_or_callback.answer(
            text=SETTINGS_HEADER_TEXT.format(
                count=len(active_subs),
                sources=sources_text,
            ),
            reply_markup=kb,
        )

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    await show_settings(message.from_user.id, message)

@router.callback_query(lambda c: c.data == "change_language")
async def change_language(cb: CallbackQuery):
    from bot.handlers.subscriptions import build_languages_kb
    sel = get_selection(cb.from_user.id)
    sel.clear()
    clear_source_selection_context(cb.from_user.id)
    kb = await build_languages_kb()
    await cb.message.edit_text(
        text=CHANGE_LANGUAGE_HEADER_TEXT,
        reply_markup=kb,
    )
    await cb.answer()

@router.callback_query(lambda c: c.data == "remove_subscriptions")
async def remove_subscriptions(cb: CallbackQuery):
    user = users_repo.get_by_telegram_id(
        telegram_id=str(cb.from_user.id),
    )
    if user:
        subscriptions_repo.deactivate_all_for_user(
            user_id=user.id,
        )

    sel = get_selection(cb.from_user.id)
    sel.clear()
    clear_source_selection_context(cb.from_user.id)
    from bot.handlers.sources import build_sources_kb
    kb = await build_sources_kb(
        selected=set(),
    )
    await cb.message.edit_text(
        text=WELCOME_NEW_USER_TEXT,
        reply_markup=kb,
    )
    await cb.answer()