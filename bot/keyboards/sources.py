from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.db.models import Source
from app.db.session import get_sync_db


async def build_sources_kb():
    db = get_sync_db()
    try:
        sources = db.execute(
            select(Source).where(Source.is_active)
        ).scalars().all()
    finally:
        db.close()

    builder = InlineKeyboardBuilder()
    for src in sources:
        builder.button(text=src.name, callback_data=f"toggle_src:{src.id}")
    builder.button(text="Next ▶️", callback_data="sources_done")
    builder.adjust(2)
    return builder.as_markup()
