from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession


class AsyncUnitOfWork:
    """Unit-of-Work wrapper for AsyncSession transactions.

    Usage:
        async with AsyncUnitOfWork(session) as db:
            ... # use db
    On success commits; on error rolls back.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session: AsyncSession = session
        self._transaction_ctx = None

    async def __aenter__(
        self,
    ) -> AsyncSession:
        self._transaction_ctx = self._session.begin()
        await self._transaction_ctx.__aenter__()
        return self._session

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> Optional[bool]:
        # __aexit__ on the underlying context will commit if exc_type is None,
        # otherwise it will roll back.
        await self._transaction_ctx.__aexit__(
            exc_type,
            exc,
            tb,
        )
        # Do not suppress exceptions
        return False


