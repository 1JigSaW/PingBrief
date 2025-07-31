from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from uuid import UUID

from app.db.models import User, Subscription, Language
from app.db.session import get_sync_db

router = Router()
_selection: dict[int, set[UUID]] = {}

async def build_languages_kb():
    db = get_sync_db()
    try:
        langs = db.query(Language).filter_by().all()
    finally:
        db.close()
    kb = InlineKeyboardBuilder()
    for lang in langs:
        kb.button(text=lang.name, callback_data=f"lang:{lang.code}")
    kb.adjust(2)
    return kb.as_markup()

@router.callback_query(lambda c: c.data and c.data.startswith("sources_done"))
async def sources_done(cb: CallbackQuery):
    kb = await build_languages_kb()
    await cb.message.edit_text("Выберите язык для подписки:", reply_markup=kb)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def language_chosen(cb: CallbackQuery):
    code = cb.data.split(":",1)[1]
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(cb.from_user.id)).one_or_none()
        if not user:
            user = User(telegram_id=str(cb.from_user.id), username=cb.from_user.username)
            db.add(user); db.commit()
        for src_id in _selection.pop(cb.from_user.id, []):
            sub = Subscription(
                user_id=user.id,
                source_id=src_id,
                language=code,
                is_active=True,
            )
            db.add(sub)
        db.commit()
    finally:
        db.close()

    await cb.message.edit_text(
        f"Подписка на язык «{code}» создана. Ждите новостей!",
        reply_markup=None
    )
    await cb.answer()
