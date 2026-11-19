from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "postgresql+psycopg://eklavya:eklavya@127.0.0.1:5432/eklavya"
    log_level: str = "INFO"
    seed_file: Path = ROOT / "challenges" / "catalog.json"
    test_seed_file: Path = ROOT / "challenges" / "tests.json"
    evaluator_seed_file: Path = ROOT / "challenges" / "evaluators.json"
    secret_key: str = "local-development-secret-change-before-deployment"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    public_url: str = "http://localhost:3000"
    redis_url: str = "redis://127.0.0.1:6379/0"


@lru_cache
def settings() -> Settings:
    return Settings()
