from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "postgresql+psycopg://eklavya:eklavya@127.0.0.1:5432/eklavya"
    log_level: str = "INFO"
    seed_file: Path = ROOT / "challenges" / "catalog.json"


@lru_cache
def settings() -> Settings:
    return Settings()
