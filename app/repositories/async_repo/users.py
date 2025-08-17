from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.schemas import UserCreate


async def get_by_id(
    db: AsyncSession,
    user_id: UUID,
) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    user_in: UserCreate,
) -> User:
    data = user_in.model_dump()
    user = User(**data)
    db.add(user)
    # Commit at UoW level
    await db.flush()
    await db.refresh(user)
    return user


