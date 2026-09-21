from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_provider: str = Field(default="ollama", pattern="^(gemini|ollama)$")
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.7-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    database_url: str = "sqlite:///./data/utp_assistant.db"
    max_tool_iterations: int = Field(default=5, ge=1, le=20)
    frontend_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
