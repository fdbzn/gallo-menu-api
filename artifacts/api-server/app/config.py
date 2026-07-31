"""Application settings loaded from environment variables."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]  -- values come from env vars
