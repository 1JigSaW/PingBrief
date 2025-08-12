"""Helpers for commonly used one-liner keyboards (returns markup)."""

from aiogram.utils.keyboard import InlineKeyboardBuilder


def as_markup(
    builder: InlineKeyboardBuilder,
):
    return builder.as_markup()

