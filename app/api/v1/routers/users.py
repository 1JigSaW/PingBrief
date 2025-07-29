from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.db.session import get_db
from app.crud.crud_user import CRUDUser
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
    user = await CRUDUser.create(db, user_in)
    return user


@router.get(
    "/{user_id}",
    response_model=UserRead,
)
async def read_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    user = await CRUDUser.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
