from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DBVAULT_",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "dev"
    database_url: str = "sqlite:///./dbvault.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    refresh_token_expire_minutes: int = 60 * 24 * 7
    encryption_key: str | None = None
    backup_tmp_dir: Path = Path("./dbvault_tmp")
    local_storage_root: Path = Path("./dbvault_backups")
    log_level: str = "INFO"
    openapi_enabled: bool = True
    run_background_tasks_inline: bool = False
    scheduler_enabled: bool = True
    enable_registration: bool = False
    initial_admin_username: str = "admin"
    initial_admin_password: str = Field(default="admin123456789", min_length=12)


@lru_cache
def get_settings() -> Settings:
    return Settings()
