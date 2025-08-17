PingBrief Code Structure

Layers
- app/repositories/*: sync repositories (Telegram bot)
- app/repositories/async_repo/*: async repositories (FastAPI)
- app/db/uow.py, app/db/uow_sync.py: Unit-of-Work for async/sync
- bot/handlers/*: thin handlers orchestrating flows
- bot/keyboards/*: keyboard builders
- bot/texts.py: centralized UI texts
- bot/utils/*: UI helpers (flags, etc.)

Guidelines
- Keep handlers thin; push DB logic to repositories.
- Use UoW to manage transactions; repositories avoid committing.
- Name every function argument; put each on a new line.
- Keep strings in bot/texts.py.
- Prefer explicit, readable code over clever one-liners.

Running
- API: uvicorn app.main:app (env via .env)
- Bot: python -m bot.main


