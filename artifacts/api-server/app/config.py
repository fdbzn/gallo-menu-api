"""Application settings loaded from environment variables.

Priority: OS env vars > .env file (optional, local dev only).
Cloud Run provides vars directly — no .env file needed.
"""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: str
    app_deep_link: str = "muchi://login"
    app_password_reset_deep_link: str = "muchi://reset-password"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        extra="ignore",
    )

    @field_validator("supabase_jwt_secret", mode="before")
    @classmethod
    def strip_jwt_secret_quotes(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value


settings = Settings()
