import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_optional_int_env(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return int(value)


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_sales_crm",
    )
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    FRONTEND_URL: str | None = os.getenv("FRONTEND_URL")
    BACKEND_URL: str | None = os.getenv("BACKEND_URL")
    TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_SECRET: str | None = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    TELEGRAM_ADMIN_CHAT_ID: str | None = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    DEFAULT_BUSINESS_ID: int | None = get_optional_int_env("DEFAULT_BUSINESS_ID")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str | None = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str | None = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def __init__(self) -> None:
        if self.APP_ENV == "production" and self.JWT_SECRET_KEY == "change-me":
            raise RuntimeError("JWT_SECRET_KEY must be configured in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
