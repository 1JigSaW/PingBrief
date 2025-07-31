from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards.sources import build_sources_kb

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = await build_sources_kb()
    await message.answer("Welcome! Choose your sources:", reply_markup=kb)