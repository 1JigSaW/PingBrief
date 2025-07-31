from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from fastapi import Depends

from app.db.session import get_db
from bot.keyboards.sources import build_sources_kb

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, db=Depends(get_db)):
    kb = await build_sources_kb(db)
    await message.answer("Please choose sources:", reply_markup=kb)
