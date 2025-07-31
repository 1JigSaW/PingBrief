import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.telegram_bot_token, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def on_start(message: Message):
    await message.answer("👋 Welcome! Use /subscribe to manage your news sources.")

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
