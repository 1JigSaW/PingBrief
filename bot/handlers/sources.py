from aiogram import Router
from aiogram.types import CallbackQuery
from fastapi import Depends

from app.db.models import Subscription, User
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db

router = Router()
_selection = {}

@router.callback_query(lambda c: c.data and c.data.startswith("toggle_src:"))
async def toggle_source(cb: CallbackQuery, db=Depends(get_db)):
    src_id = UUID(cb.data.split(":", 1)[1])
    chat = cb.from_user.id
    sel = _selection.setdefault(chat, set())
    if src_id in sel:
        sel.remove(src_id)
    else:
        sel.add(src_id)
    await cb.answer(f"Selected: {len(sel)}")

@router.callback_query(lambda c: c.data == "sources_done")
async def sources_done(cb: CallbackQuery, db=Depends(get_db)):
    chat = cb.from_user
    user = (await db.execute(select(User).where(User.telegram_id==str(chat.id)))).scalar_one_or_none()
    if not user:
        user = User(telegram_id=str(chat.id), username=chat.username)
        db.add(user)
        await db.commit()
    for src_id in _selection.get(chat.id, []):
        sub = Subscription(user_id=user.id, source_id=src_id, language="en")
        db.add(sub)
    await db.commit()
    await cb.message.edit_text("Sources saved. Now choose a language.", reply_markup=None)
