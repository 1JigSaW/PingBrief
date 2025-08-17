from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session


class SyncUnitOfWork:
    """Unit-of-Work wrapper for sync SQLAlchemy Session.

    Usage:
        with SyncUnitOfWork(session) as db:
            ...  # use db
    On success commits; on error rolls back.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session: Session = session

    def __enter__(
        self,
    ) -> Session:
        return self._session

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> Optional[bool]:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
        # Do not suppress exceptions
        return False


