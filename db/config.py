import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://hkcc:hkcc@localhost:5432/hkcc"
    api_base_url: str = "http://localhost:8000"
    hkcc_release_tag: str = "dev"


def get_settings() -> Settings:
    url = os.environ.get("DATABASE_URL")
    if url:
        return Settings(database_url=url)
    return Settings()
