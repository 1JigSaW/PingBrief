from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class UserBase(BaseModel):
    telegram_id: str | None
    username: str | None
    first_name: str | None
    last_name: str | None
    is_active: bool


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
