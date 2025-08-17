from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.db.session import get_db
from app.repositories.async_repo import users as users_repo
from app.db.uow import AsyncUnitOfWork
from app.schemas import UserRead, UserCreate

router = APIRouter(prefix="/users")

@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    async with AsyncUnitOfWork(db) as uow:
        user = await users_repo.create(
            db=uow,
            user_in=user_in,
        )
        return user


@router.get(
    "/{user_id}",
    response_model=UserRead,
)
async def read_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await users_repo.get_by_id(
        db=db,
        user_id=user_id,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
