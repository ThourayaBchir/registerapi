from functools import lru_cache

from pydantic import EmailStr, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    email_api_url: HttpUrl
    system_email: EmailStr
    basic_auth_username: str = "admin"
    basic_auth_password: str = "changeme"
    secret_key: str
    activation_code_ttl_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
