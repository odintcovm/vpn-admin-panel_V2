from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VPN Admin Panel API"
    app_provider: str = "mock"
    database_url: str = "sqlite:///./data.db"
    api_token: str = "admin-token"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
