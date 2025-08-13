from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import User, Subscription
from app.db.session import get_sync_db
from bot.state import get_selection, set_source_selection_context, clear_source_selection_context
from bot.keyboards.builders import (
    build_start_keyboard,
    build_help_keyboard,
    build_command_shortcuts_keyboard,
    build_settings_keyboard,
    build_go_start_keyboard,
)
from bot.texts import (
    WELCOME_NEW_USER_TEXT,
    WELCOME_EXISTING_USER_TEXT,
    HELP_TEXT,
    UNKNOWN_COMMAND_TEXT,
    NO_SUBSCRIPTIONS_TEXT,
    NO_ACTIVE_SUBSCRIPTIONS_TEXT,
    SETTINGS_HEADER_TEXT,
)

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(message.from_user.id)).one_or_none()
        
        if user and user.subscriptions:
            sources_info = [
                f"📰 <b>{sub.source.name}</b> ({sub.language})"
                for sub in user.subscriptions
                if sub.is_active
            ]

            if sources_info:
                sources_text = "\n".join(sources_info)
                kb = build_start_keyboard().as_markup()
                await message.answer(
                    text=WELCOME_EXISTING_USER_TEXT.format(
                        count=len(sources_info),
                        sources=sources_text,
                    ),
                    reply_markup=kb,
                )
                return

        if not user:
            user = User(
                telegram_id=str(message.from_user.id), 
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            db.add(user)
            db.commit()

        from bot.handlers.sources import build_sources_kb
        kb = await build_sources_kb(set())
        await message.answer(
            text=WELCOME_NEW_USER_TEXT,
            reply_markup=kb,
        )
    finally:
        db.close()

@router.message(Command("help"))
async def cmd_help(message: Message):
    kb = build_help_keyboard().as_markup()
    await message.answer(
        text=HELP_TEXT,
        reply_markup=kb,
    )

@router.message(F.text.startswith("/"))
async def unknown_command(message: Message):
    kb = build_command_shortcuts_keyboard().as_markup()
    await message.answer(
        text=UNKNOWN_COMMAND_TEXT,
        reply_markup=kb,
    )

@router.callback_query(lambda c: c.data == "change_source")
async def change_source(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    sel.clear()
    # Preselect currently active sources
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
        if user:
            active_subs = [sub for sub in user.subscriptions if sub.is_active]
            for sub in active_subs:
                sel.add(sub.source_id)
    finally:
        db.close()
    set_source_selection_context(chat, "settings")

    from bot.handlers.sources import build_sources_kb
    kb = await build_sources_kb(
        selected=sel,
        context="settings",
    )
    await cb.message.edit_text(
        text="📰 <b>Change Sources</b>\n\nSelect one or more sources:",
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

@router.callback_query(lambda c: c.data == "cmd_help")
async def cmd_help_button(cb: CallbackQuery):
    await cmd_help(cb.message)
    await cb.answer()

async def show_settings(user_id: int, message_or_callback):
    """Render the settings screen for both message and callback contexts."""
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(user_id)).one_or_none()
        if user:
            db.refresh(user)
        
        if not user or not user.subscriptions:
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

        active_subs = [sub for sub in user.subscriptions if sub.is_active]
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
        
        sources_info = []
        for sub in active_subs:
            sources_info.append(f"📰 <b>{sub.source.name}</b> ({sub.language})")
        
        sources_text = "\n".join(sources_info)
        
        kb = build_settings_keyboard().as_markup()
        
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
    finally:
        db.close()

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
        text="🌍 <b>Change Language</b>\n\nSelect your preferred language:",
        reply_markup=kb,
    )
    await cb.answer()

@router.callback_query(lambda c: c.data == "remove_subscriptions")
async def remove_subscriptions(cb: CallbackQuery):
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
        if user:
            for sub in user.subscriptions:
                sub.is_active = False
            db.commit()
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🚀 /start", callback_data="cmd_start")
        kb.adjust(1)
        
        await cb.message.edit_text(
            "🗑️ <b>Subscription removed</b>\n\n"
            "✅ Your subscription has been deactivated.\n\n"
            "Click the button below to create a new subscription!",
            reply_markup=kb.as_markup()
        )
    finally:
        db.close()
    await cb.answer()