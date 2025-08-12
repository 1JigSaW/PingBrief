from uuid import UUID

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.db.models import Source, User, Subscription
from app.db.session import get_sync_db
from bot.state import get_selection, get_source_selection_context, clear_source_selection_context
from bot.texts import SELECTED_SOURCES_TEXT

router = Router()

async def build_sources_kb(selected, context: str = "onboarding"):
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
        next_text = "➡️ Continue"
        next_callback = "sources_done" if context == "onboarding" else "sources_apply"
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
        sel.clear()
        sel.add(src_id)
    context = get_source_selection_context(chat)
    kb = await build_sources_kb(sel, context=context)
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

    context = get_source_selection_context(chat)
    if context == "onboarding":
        from bot.handlers.subscriptions import build_languages_kb
        kb = await build_languages_kb()
        await cb.message.edit_text(
            text=SELECTED_SOURCES_TEXT.format(
                count=len(selected_sources),
                sources=sources_text,
            ),
            reply_markup=kb,
        )
    else:
        db = get_sync_db()
        try:
            user = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
            if user:
                sub = (
                    db.query(Subscription)
                    .filter(
                        Subscription.user_id == user.id,
                        Subscription.is_active == True,
                    )
                    .first()
                )
                if sub:
                    new_source_id = next(iter(sel))
                    sub.source_id = new_source_id
                    db.commit()
        finally:
            db.close()
        clear_source_selection_context(chat)
        from bot.state import pop_selection as _pop_selection
        _pop_selection(chat)
        from bot.handlers.start import show_settings
        await show_settings(cb.from_user.id, cb.message)
    await cb.answer()

@router.callback_query(lambda c: c.data == "sources_apply")
async def sources_apply(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    if len(sel) == 0:
        await cb.answer("⚠️ Please select at least one news source to continue", show_alert=True)
        return

    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
        if not user:
            await cb.answer("User not found", show_alert=True)
            return
        sub = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
            )
            .first()
        )
        if not sub:
            await cb.answer("No active subscription", show_alert=True)
            return
        new_source_id = next(iter(sel))
        sub.source_id = new_source_id
        db.commit()
    finally:
        db.close()

    # Clear selection and return to settings view
    from bot.state import pop_selection as _pop_selection
    _pop_selection(chat)
    from bot.handlers.start import show_settings
    await show_settings(cb.from_user.id, cb.message)
    await cb.answer()
