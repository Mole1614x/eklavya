from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "postgresql+psycopg://eklavya:eklavya@127.0.0.1:5432/eklavya"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    seed_file: Path = ROOT / "challenges" / "catalog.json"
    test_seed_file: Path = ROOT / "challenges" / "tests.json"
    evaluator_seed_file: Path = ROOT / "challenges" / "evaluators.json"
    gamification_seed_file: Path = ROOT / "challenges" / "gamification.json"
    learning_paths_seed_file: Path = ROOT / "challenges" / "paths.json"
    dataset_storage_dir: Path = ROOT / "var" / "datasets"
    dataset_max_bytes: int = 5 * 1024 * 1024
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout_seconds: int = 10
    public_cache_seconds: int = 30
    judge_stuck_seconds: int = 60
    secret_key: str = "local-development-secret-change-before-deployment"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    public_url: str = "http://localhost:3000"
    redis_url: str = "redis://127.0.0.1:6379/0"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_hosts: str = "localhost,127.0.0.1,testserver,backend"
    rate_limit_enabled: bool = False
    readiness_check_redis: bool = False

    @property
    def origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def host_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if self.secret_key == "local-development-secret-change-before-deployment" or len(self.secret_key) < 32:
                raise ValueError("Production SECRET_KEY must be an unpredictable value of at least 32 characters")
            if not self.origin_list or "*" in self.origin_list:
                raise ValueError("Production ALLOWED_ORIGINS must be an explicit allowlist")
            if not self.host_list or "*" in self.host_list:
                raise ValueError("Production ALLOWED_HOSTS must be an explicit allowlist")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise ValueError("Production DATABASE_URL must use PostgreSQL")
            if "eklavya:eklavya@127.0.0.1" in self.database_url:
                raise ValueError("Production DATABASE_URL must not use the development credentials")
            parsed_redis = urlsplit(self.redis_url)
            if parsed_redis.scheme not in {"redis", "rediss"}:
                raise ValueError("Production REDIS_URL must use Redis")
            if not parsed_redis.password:
                raise ValueError("Production REDIS_URL must authenticate to Redis")
            if urlsplit(self.public_url).scheme != "https":
                raise ValueError("Production PUBLIC_URL must use HTTPS")
            if any(urlsplit(origin).scheme != "https" or not urlsplit(origin).netloc for origin in self.origin_list):
                raise ValueError("Production ALLOWED_ORIGINS entries must be absolute HTTPS origins")
            if not self.rate_limit_enabled or not self.readiness_check_redis:
                raise ValueError("Production rate limiting and Redis readiness checks must be enabled")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
