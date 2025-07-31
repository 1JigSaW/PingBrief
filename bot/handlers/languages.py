from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.db.models import Language, User, Subscription
from app.db.session import get_sync_db
from bot.state import pop_selection

router = Router()

async def build_languages_kb():
    db = get_sync_db()
    try:
        langs = db.query(Language).all()
    finally:
        db.close()

    builder = InlineKeyboardBuilder()
    for lang in langs:
        builder.button(text=lang.name, callback_data=f"lang:{lang.code}")
    builder.adjust(2)
    return builder.as_markup()

@router.callback_query(lambda c: c.data.startswith("lang:"))
async def lang_chosen(cb: CallbackQuery):
    code = cb.data.split(":",1)[1]
    chat_id = cb.from_user.id
    db = get_sync_db()
    try:
        user = db.query(User).filter_by(telegram_id=str(chat_id)).one_or_none()
        if not user:
            user = User(telegram_id=str(chat_id), username=cb.from_user.username)
            db.add(user); db.commit()
        for src_id in pop_selection(chat_id):
            sub = Subscription(user_id=user.id, source_id=src_id, language=code, is_active=True)
            db.add(sub)
        db.commit()
    finally:
        db.close()

    await cb.message.edit_text(f"Подписка на язык «{code}» создана. Ждите новостей!", reply_markup=None)
    await cb.answer()
