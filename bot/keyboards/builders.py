"""Inline keyboard builders used across handlers.

Separated from handlers to keep them simple and focused on flow control.
"""

from typing import Iterable

from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_help_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Get Started",
        callback_data="start_new",
    )
    builder.button(
        text="⚙️ Settings",
        callback_data="go_settings",
    )
    builder.button(
        text="📋 /start",
        callback_data="cmd_start",
    )
    builder.button(
        text="⚙️ /settings",
        callback_data="cmd_settings",
    )
    builder.button(
        text="❓ /help",
        callback_data="cmd_help",
    )
    builder.adjust(2)
    return builder


def build_command_shortcuts_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 /start",
        callback_data="cmd_start",
    )
    builder.button(
        text="⚙️ /settings",
        callback_data="cmd_settings",
    )
    builder.button(
        text="❓ /help",
        callback_data="cmd_help",
    )
    builder.adjust(1)
    return builder


def build_settings_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="➕ Add new subscription",
        callback_data="add_subscription",
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
    builder.button(
        text="➕ Add New Subscription",
        callback_data="start_new",
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

