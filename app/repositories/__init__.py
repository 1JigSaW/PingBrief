"""Repository layer for database access.

Synchronous repositories are used by the Telegram bot (aiogram) where
sync SQLAlchemy sessions are appropriate. For FastAPI async endpoints,
use repositories under `app.repositories.async_repo`.
"""


