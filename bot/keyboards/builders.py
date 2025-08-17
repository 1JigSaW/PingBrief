"""Inline keyboard builders used across handlers.

Separated from handlers to keep them simple and focused on flow control.
"""

from typing import Iterable
from app.db.session import get_sync_db
from app.db.models import User
from datetime import datetime
from app.repositories import users as users_repo

from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_help_keyboard() -> InlineKeyboardBuilder:
    return build_command_shortcuts_keyboard()


def build_command_shortcuts_keyboard(user_id: int | None = None) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 /start",
        callback_data="cmd_start",
    )
    builder.button(
        text="⚙️ /settings",
        callback_data="cmd_settings",
    )
    show_premium = True
    if user_id is not None:
        has_premium = users_repo.has_active_premium(
            telegram_id=str(user_id),
        )
        if has_premium:
            show_premium = False
    if show_premium:
        builder.button(
            text="⭐ /premium",
            callback_data="open_premium",
        )
    builder.adjust(1)
    return builder


def build_settings_keyboard(user_id: int | None = None) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📰 Change sources",
        callback_data="change_source",
    )
    builder.button(
        text="🌍 Change language",
        callback_data="change_language",
    )
    show_premium = True
    if user_id is not None:
        has_premium = users_repo.has_active_premium(
            telegram_id=str(user_id),
        )
        if has_premium:
            show_premium = False
    if show_premium:
        builder.button(
            text="⭐ Premium",
            callback_data="open_premium",
        )
    builder.button(
        text="🗑️ Remove subscription",
        callback_data="remove_subscriptions",
    )
    builder.adjust(1)
    return builder


def build_start_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⚙️ Manage Subscriptions",
        callback_data="go_settings",
    )
    builder.adjust(1)
    return builder


def build_go_start_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 /start",
        callback_data="cmd_start",
    )
    builder.adjust(1)
    return builder


def build_paywall_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⭐ Buy Premium",
        callback_data="open_premium",
    )
    builder.button(
        text="✅ Keep 1 source",
        callback_data="keep_one_source",
    )
    builder.button(
        text="◀️ Back",
        callback_data="back_to_selection",
    )
    builder.adjust(1)
    return builder


def build_paywall_keyboard_with_keep_options(
    options: list[tuple[str, str]],
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⭐ Buy Premium",
        callback_data="open_premium",
    )
    for label, source_id in options:
        builder.button(
            text=f"✅ Keep {label}",
            callback_data=f"keep_one_source:{source_id}",
        )
    builder.button(
        text="◀️ Back",
        callback_data="back_to_selection",
    )
    builder.adjust(1)
    return builder

