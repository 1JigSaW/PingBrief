from functools import lru_cache
from typing import List, Optional

from pydantic import AnyUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str
    api_v1_str: str
    secret_key: str
    debug: bool

    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_url: Optional[PostgresDsn | str]

    redis_host: str
    redis_port: int

    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None

    newsapi_key: Optional[str] = None

    telegram_bot_token: str
    webhook_url: Optional[AnyUrl] = Field(None, alias="TELEGRAM_WEBHOOK_URL")

    broker_url: Optional[str] = None
    result_backend: Optional[str] = None
    beat_schedule: Optional[int] = None

    allowed_hosts: List[str] = Field(default_factory=lambda: ["*"])

    @field_validator("database_url", mode="before")
    def _assemble_database_url(cls, v, info):
        if v is not None:
            return v
        d = info.data
        return (
            f"postgresql+asyncpg://{d['postgres_user']}:"
            f"{d['postgres_password']}@"
            f"{d['postgres_host']}:"
            f"{d['postgres_port']}/"
            f"{d['postgres_db']}"
        )

    @field_validator("broker_url", mode="before")
    def _assemble_broker_url(cls, v, info):
        if v is not None:
            return v
        d = info.data
        return f"redis://{d['redis_host']}:{d['redis_port']}/0"

    @field_validator("result_backend", mode="before")
    def _assemble_result_backend(cls, v, info):
        if v is not None:
            return v
        d = info.data
        return f"redis://{d['redis_host']}:{d['redis_port']}/1"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
