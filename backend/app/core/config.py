from functools import lru_cache
import secrets

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EA_", env_file=".env", extra="ignore")

    environment: str = "development"
    secret_key: str = secrets.token_urlsafe(48)
    database_url: str = "sqlite:///./backend/ea_workbench.db"
    access_token_minutes: int = 30
    cookie_secure: bool = False
    cors_origins: str = ""
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    mistral_api_key: str = ""
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-small-latest"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() != "development":
            if len(self.secret_key) < 32:
                raise ValueError("EA_SECRET_KEY must contain at least 32 characters outside development")
            if not self.cookie_secure:
                raise ValueError("EA_COOKIE_SECURE must be enabled outside development")
        return self

    def create_engine(self) -> Engine:
        options = {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        return create_engine(self.database_url, connect_args=options, pool_pre_ping=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()