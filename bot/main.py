from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import get_settings

settings = get_settings()

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(
        parse_mode="HTML",
    ),
)
dp = Dispatcher(storage=MemoryStorage())

from bot.handlers import start, sources, subscriptions, premium

dp.include_router(start.router)
dp.include_router(sources.router)
dp.include_router(subscriptions.router)
dp.include_router(premium.router)

if __name__ == "__main__":
    dp.run_polling(bot)
