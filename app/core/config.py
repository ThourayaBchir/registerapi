from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    smtp_host: str
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    basic_auth_username: str = "admin"
    basic_auth_password: str = "changeme"
    secret_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
