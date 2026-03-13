from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VPN Admin Panel API"
    app_provider: str = "mock"
    database_url: str = "sqlite:///./data.db"
    api_token: str = "admin-token"

    app_env: str = "development"
    dev_role_emulation: bool = False
    schema_management_mode: str = "alembic"  # alembic | bootstrap

    auth_enabled: bool = True
    auth_cookie_name: str = "vpn_admin_session"
    auth_session_ttl_hours: int = 24
    auth_cookie_secure: bool = False

    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_password_hash: str = ""

    deploy_mode: str = "safe"
    providers_enabled: str = "xray,wg,avg,mock"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_dev_like(self) -> bool:
        return self.app_env in {"development", "dev", "local", "test"}

    @property
    def is_prod_like(self) -> bool:
        return self.app_env in {"production", "prod", "staging"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
