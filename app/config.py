from functools import lru_cache
from typing import List, Optional

from pydantic import AnyUrl, BaseSettings, Field, PostgresDsn, validator


class Settings(BaseSettings):
    """App settings loaded from .env or the OS environment."""

    app_env: str = Field("local", env="APP_ENV")
    api_v1_str: str = Field("/api/v1", env="API_V1_STR")
    secret_key: str = Field(..., env="SECRET_KEY")
    debug: bool = Field(False, env="DEBUG")

    # ------------------------------------------------------------------
    # Database (PostgreSQL via asyncpg)
    # ------------------------------------------------------------------
    postgres_host: str = Field("db", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_db: str = Field("pingbrief", env="POSTGRES_DB")
    postgres_user: str = Field("pingbrief", env="POSTGRES_USER")
    postgres_password: str = Field("pingbrief", env="POSTGRES_PASSWORD")
    database_url: Optional[PostgresDsn | str] = Field(None, env="DATABASE_URL")

    # ------------------------------------------------------------------
    # Redis (broker / cache)
    # ------------------------------------------------------------------
    redis_host: str = Field("redis", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")

    # ------------------------------------------------------------------
    # OpenAI / LLM
    # ------------------------------------------------------------------
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")

    # ------------------------------------------------------------------
    # External APIs
    # ------------------------------------------------------------------
    newsapi_key: Optional[str] = Field(None, env="NEWSAPI_KEY")

    # ------------------------------------------------------------------
    # Telegram
    # ------------------------------------------------------------------
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    webhook_url: Optional[AnyUrl] = Field(None, env="WEBHOOK_URL")

    # ------------------------------------------------------------------
    # Celery
    # ------------------------------------------------------------------
    broker_url: Optional[str] = Field(None, env="CELERY_BROKER_URL")
    result_backend: Optional[str] = Field(None, env="CELERY_RESULT_BACKEND")
    beat_schedule: int = Field(15, env="FEED_FETCH_INTERVAL_MIN")  # minutes

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    allowed_hosts: List[str] = Field(["*"], env="ALLOWED_HOSTS")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @validator("database_url", pre=True)
    def assemble_db_uri(cls, v: Optional[str], values: dict[str, str]) -> str:
        """Create DATABASE_URL from individual parts if not provided."""
        if v:
            return v
        return (
            f"postgresql+asyncpg://{values['postgres_user']}:{values['postgres_password']}@"
            f"{values['postgres_host']}:{values['postgres_port']}/{values['postgres_db']}"
        )

    @validator("broker_url", pre=True, always=True)
    def default_broker(cls, v: Optional[str], values: dict[str, str]) -> str:
        if v:
            return v
        return f"redis://{values['redis_host']}:{values['redis_port']}/0"

    @validator("result_backend", pre=True, always=True)
    def default_backend(cls, v: Optional[str], values: dict[str, str]) -> str:
        if v:
            return v
        return f"redis://{values['redis_host']}:{values['redis_port']}/1"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings object for the lifetime of the process."""
    return Settings()