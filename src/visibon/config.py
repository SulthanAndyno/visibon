from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VISIBON_", extra="ignore")

    extractor: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3-vl:2b"
    ollama_timeout: float = 180.0

    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = "gemini-3.8-flash"

    telegram_bot_token: str | None = Field(default=None, validation_alias="TELEGRAM_BOT_TOKEN")
    database_path: str = "visibon.db"

    max_image_side: int = 900
    blur_threshold: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
