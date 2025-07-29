from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.db.models import User
from app.schemas import UserCreate


class CRUDUser:
    @staticmethod
    async def get_by_id(
            db: AsyncSession,
            user_id: UUID,
    ):
        result = await db.execute(
            select(User)
            .where(User.id==user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
            db: AsyncSession,
            obj_in: UserCreate,
    ) -> User:
        db_obj = User(**obj_in.dict())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj