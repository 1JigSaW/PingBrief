from uuid import UUID

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.db.models import Source
from app.db.session import get_sync_db
from bot.state import get_selection
from bot.texts import SELECTED_SOURCES_TEXT

router = Router()

async def build_sources_kb(selected):
    db = get_sync_db()
    try:
        sources = db.execute(select(Source).where(Source.is_active)).scalars().all()
    finally:
        db.close()

    builder = InlineKeyboardBuilder()
    for src in sources:
        mark = "✅ " if src.id in selected else "📰 "
        builder.button(text=f"{mark}{src.name}", callback_data=f"toggle_src:{src.id}")

    if len(selected) > 0:
        next_text = f"➡️ Continue ({len(selected)} selected)"
        next_callback = "sources_done"
    else:
        next_text = "⚠️ Select at least one source"
        next_callback = "no_sources_selected"
    
    builder.button(text=next_text, callback_data=next_callback)
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

@router.callback_query(lambda c: c.data == "no_sources_selected")
async def no_sources_selected(cb: CallbackQuery):
    await cb.answer("⚠️ Please select at least one news source to continue", show_alert=True)

@router.callback_query(lambda c: c.data == "sources_done")
async def sources_done(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    
    if len(sel) == 0:
        await cb.answer("⚠️ Please select at least one news source to continue", show_alert=True)
        return

    db = get_sync_db()
    try:
        selected_sources = db.query(Source).filter(Source.id.in_([str(s) for s in sel])).all()
        sources_text = "\n".join([f"📰 <b>{src.name}</b>" for src in selected_sources])
    finally:
        db.close()

    from bot.handlers.subscriptions import build_languages_kb
    kb = await build_languages_kb()
    await cb.message.edit_text(
        text=SELECTED_SOURCES_TEXT.format(
            count=len(selected_sources),
            sources=sources_text,
        ),
        reply_markup=kb,
    )
    await cb.answer()
