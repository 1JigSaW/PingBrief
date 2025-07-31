from uuid import UUID

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.db.models import Source
from app.db.session import get_sync_db
from bot.handlers.subscriptions import build_languages_kb
from bot.state import get_selection

router = Router()

async def build_sources_kb(selected):
    db = get_sync_db()
    try:
        sources = db.execute(select(Source).where(Source.is_active)).scalars().all()
    finally:
        db.close()

    builder = InlineKeyboardBuilder()
    for src in sources:
        mark = "✅ " if src.id in selected else ""
        builder.button(text=f"{mark}{src.name}", callback_data=f"toggle_src:{src.id}")
    builder.button(text="Next ▶️", callback_data="sources_done")
    builder.adjust(2)
    return builder.as_markup()

@router.callback_query(lambda c: c.data and c.data.startswith("toggle_src:"))
async def toggle_src(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    src_id = UUID(cb.data.split(":",1)[1])
    if src_id in sel:
        sel.remove(src_id)
    else:
        sel.add(src_id)
    kb = await build_sources_kb(sel)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


@router.callback_query(lambda c: c.data == "sources_done")
async def sources_done(cb: CallbackQuery):
    kb = await build_languages_kb()
    await cb.message.edit_text("Выберите язык для подписки:", reply_markup=kb)
    await cb.answer()
