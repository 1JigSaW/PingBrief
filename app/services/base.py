from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession

class BaseParser(ABC):
    def __init__(
            self,
            db: AsyncSession,
    ):
        self.db = db

    @abstractmethod
    async def fetch_all(
            self,
            limit: int = 100,
    ) -> list[dict]:
        """
        Return raw news items as list of dicts.
        """
        ...

    @abstractmethod
    async def save_all(
            self,
            limit: int = 100,
    ) -> None:
        """
        Persist new items to database and trigger notifications.
        """
        ...
