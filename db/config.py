from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "hkcc.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL
    api_base_url: str = "http://localhost:8000"
    hkcc_release_tag: str = "dev"
    # Comma-separated list of allowed origins for CORS. Empty in non-dev = no cross-origin browser access.
    hkcc_allowed_origins: str = ""
    # Optional Sentry DSN; when set, sentry_sdk is initialised in api/streamlit entrypoints.
    sentry_dsn: str = ""


def get_settings() -> Settings:
    return Settings()


def allowed_origins() -> list[str]:
    """Resolve the CORS allowlist.

    - If ``HKCC_ALLOWED_ORIGINS`` is set, use that (comma-separated).
    - Else if the release tag is ``dev``, allow ``*`` for local convenience.
    - Else default closed (empty list).
    """
    settings = get_settings()
    raw = (settings.hkcc_allowed_origins or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    if settings.hkcc_release_tag == "dev":
        return ["*"]
    return []
