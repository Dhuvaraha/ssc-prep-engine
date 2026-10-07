from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SSC Prep Engine API"
    database_url: str = "sqlite:///./ssc_prep.db"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    private_asset_dir: str = "data/private/assets"
    cors_origins: str = "http://localhost:5173"
    reviewer_emails: str = ""
    registration_enabled: bool = True
    content_audit_on_startup: bool = False
    apply_content_repair_on_startup: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
