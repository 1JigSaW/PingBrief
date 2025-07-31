from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from app.db.models import Source

async def build_sources_kb(db):
    kb = InlineKeyboardMarkup(row_width=2)
    result = await db.execute(select(Source).where(Source.is_active))
    for src in result.scalars().all():
        kb.insert(InlineKeyboardButton(
            text=src.name,
            callback_data=f"toggle_src:{src.id}"
        ))
    kb.add(InlineKeyboardButton("Next ▶️", callback_data="sources_done"))
    return kb
