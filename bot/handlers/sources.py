from uuid import UUID

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.db.models import User, Subscription
from app.db.session import get_sync_db
from app.repositories import sources as sources_repo
from app.repositories import subscriptions as subscriptions_repo
from app.repositories import users as users_repo
from bot.state import (
    get_selection,
    get_source_selection_context,
    clear_source_selection_context,
    set_last_selected_source,
    get_last_selected_source,
)
from bot.texts import (
    SELECTED_SOURCES_TEXT,
    PAYWALL_MULTIPLE_SOURCES_TEXT,
    LOADING_PREPARE_LANG_TEXT,
    LOADING_APPLY_CHANGES_TEXT,
    SELECT_AT_LEAST_ONE_SOURCE_TEXT,
    SELECT_SOURCES_HEADER_TEXT,
)
from bot.keyboards.builders import build_paywall_keyboard, build_paywall_keyboard_with_keep_options

router = Router()

async def build_sources_kb(selected, context: str = "onboarding"):
    sources = sources_repo.list_active_sources()

    builder = InlineKeyboardBuilder()
    for src in sources:
        mark = "✅ " if src.id in selected else "📰 "
        builder.button(
            text=f"{mark}{src.name}",
            callback_data=f"toggle_src:{src.id}",
        )

    if len(selected) > 0:
        next_text = "➡️ Continue"
        next_callback = "sources_done" if context == "onboarding" else "sources_apply"
    else:
        next_text = "⚠️ Select at least one source"
        next_callback = "no_sources_selected"
    
    builder.button(
        text=next_text,
        callback_data=next_callback,
    )
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
        set_last_selected_source(
            chat_id=chat,
            source_id=src_id,
        )
    context = get_source_selection_context(chat)
    if len(sel) > 1 and not users_repo.has_active_premium(
        telegram_id=str(chat),
    ):
        try:
            await cb.answer(
                text="Free plan allows 1 source. Deselect one or buy Premium.",
                show_alert=True,
            )
        except TelegramBadRequest:
            pass
        selected_sources = sources_repo.get_sources_by_ids(
            source_ids=list(sel),
        )
        last = get_last_selected_source(chat)
        ordered = sorted(selected_sources, key=lambda s: 0 if (last and s.id == last) else 1)
        options = [(s.name, str(s.id)) for s in ordered[:2]]
        kb_pay = build_paywall_keyboard_with_keep_options(options)
        await cb.message.answer(
            text=PAYWALL_MULTIPLE_SOURCES_TEXT,
            reply_markup=kb_pay.as_markup(),
        )
        return

    kb = await build_sources_kb(
        selected=sel,
        context=context,
    )
    try:
        await cb.message.edit_reply_markup(
            reply_markup=kb,
        )
    except TelegramBadRequest:
        pass
    await cb.answer()

@router.callback_query(lambda c: c.data == "no_sources_selected")
async def no_sources_selected(cb: CallbackQuery):
    await cb.answer(
        text=SELECT_AT_LEAST_ONE_SOURCE_TEXT,
        show_alert=True,
    )

@router.callback_query(lambda c: c.data == "sources_done")
async def sources_done(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    
    if len(sel) == 0:
        await cb.answer(
            text=SELECT_AT_LEAST_ONE_SOURCE_TEXT,
            show_alert=True,
        )
        return

    if len(sel) > 1 and not users_repo.has_active_premium(
        telegram_id=str(cb.from_user.id),
    ):
        selected_sources = sources_repo.get_sources_by_ids(
            source_ids=list(sel),
        )
        last = get_last_selected_source(chat)
        ordered = sorted(selected_sources, key=lambda s: 0 if (last and s.id == last) else 1)
        options = [(s.name, str(s.id)) for s in ordered[:2]]
        kb = build_paywall_keyboard_with_keep_options(options)
        await cb.message.answer(
            text=PAYWALL_MULTIPLE_SOURCES_TEXT,
            reply_markup=kb.as_markup(),
        )
        await cb.answer()
        return

    await cb.answer()
    try:
        await cb.message.edit_text(
            text=LOADING_PREPARE_LANG_TEXT,
        )
    except TelegramBadRequest:
        pass

    selected_sources = sources_repo.get_sources_by_ids(
        source_ids=list(sel),
    )
    sources_text = "\n".join([f"📰 <b>{src.name}</b>" for src in selected_sources])

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
                new_source_id = next(iter(sel))
                subscriptions_repo.set_first_active_subscription_source(
                    user_id=user.id,
                    new_source_id=new_source_id,
                )
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
        await cb.answer(
            text=SELECT_AT_LEAST_ONE_SOURCE_TEXT,
            show_alert=True,
        )
        return

    if len(sel) > 1 and not users_repo.has_active_premium(
        telegram_id=str(cb.from_user.id),
    ):
        selected_sources = sources_repo.get_sources_by_ids(
            source_ids=list(sel),
        )
        last = get_last_selected_source(chat)
        ordered = sorted(selected_sources, key=lambda s: 0 if (last and s.id == last) else 1)
        options = [(s.name, str(s.id)) for s in ordered[:2]]
        kb = build_paywall_keyboard_with_keep_options(options)
        await cb.message.answer(
            text=PAYWALL_MULTIPLE_SOURCES_TEXT,
            reply_markup=kb.as_markup(),
        )
        await cb.answer()
        return

    await cb.answer()
    try:
        await cb.message.edit_text(
            text=LOADING_APPLY_CHANGES_TEXT,
        )
    except TelegramBadRequest:
        pass

    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
        if not user:
            await cb.answer("User not found", show_alert=True)
            return

        selected_source_ids = {UUID(str(s)) for s in sel}
        subscriptions_repo.apply_sources_selection(
            user_id=user.id,
            selected_source_ids=selected_source_ids,
        )
    finally:
        db.close()

    from bot.state import pop_selection as _pop_selection
    _pop_selection(chat)
    from bot.handlers.start import show_settings
    await show_settings(cb.from_user.id, cb.message)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("keep_one_source"))
async def keep_one_source(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    if len(sel) == 0:
        await cb.answer("No sources selected", show_alert=True)
        return

    kept_id = None
    if ":" in cb.data:
        try:
            kept_id = UUID(cb.data.split(":",1)[1])
        except Exception:
            kept_id = None
    if not kept_id:
        last = get_last_selected_source(chat)
        kept_id = last if last in sel else next(iter(sel))
    sel.clear()
    sel.add(kept_id)

    from bot.handlers.subscriptions import build_languages_kb
    kb = await build_languages_kb()
    selected_sources = sources_repo.get_sources_by_ids(
        source_ids=list(sel),
    )
    sources_text = "\n".join([f"📰 <b>{src.name}</b>" for src in selected_sources])

    await cb.message.edit_text(
        text=SELECTED_SOURCES_TEXT.format(
            count=1,
            sources=sources_text,
        ),
        reply_markup=kb,
    )
    await cb.answer()

@router.callback_query(lambda c: c.data == "back_to_selection")
async def back_to_selection(cb: CallbackQuery):
    chat = cb.from_user.id
    sel = get_selection(chat)
    context = get_source_selection_context(chat)
    kb = await build_sources_kb(
        selected=sel,
        context=context,
    )
    await cb.message.edit_text(
        text=SELECT_SOURCES_HEADER_TEXT,
        reply_markup=kb,
    )
    await cb.answer()
