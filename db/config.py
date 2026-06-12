from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "hkcc.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def _resolve_version() -> str:
    """Single source of truth for the app version is ``pyproject.toml``.

    In a source checkout we parse ``pyproject.toml`` directly, so bumping that
    one number takes effect immediately (no reinstall needed). In a built/
    installed package — where ``pyproject.toml`` isn't shipped — we fall back to
    the installed package metadata. Either way the version is never duplicated
    in code.
    """
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if pyproject.is_file():
        import tomllib

        with pyproject.open("rb") as fh:
            return tomllib.load(fh)["project"]["version"]
    try:
        return version("hkcc")
    except PackageNotFoundError:
        return "0+unknown"


APP_NAME = "hKCC"
APP_TITLE = "Key Characteristics of Human Carcinogens"
APP_VERSION = _resolve_version()
APP_DEVELOPER = "Data Analysis Team @KaziLab.se"
APP_CONTACT_EMAIL = "hkcc@kazilab.se"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL
    api_base_url: str = "http://localhost:8000"
    # Override the version stamp used in /health, citations and Sentry. Left empty
    # it falls back to APP_VERSION (see release_tag), so the version only ever has
    # to be set in one place: pyproject.toml.
    hkcc_release_tag: str = ""
    # Comma-separated list of allowed origins for CORS. Empty in non-dev = no cross-origin browser access.
    hkcc_allowed_origins: str = ""
    # Optional Sentry DSN; when set, sentry_sdk is initialised in api/streamlit entrypoints.
    sentry_dsn: str = ""

    @property
    def release_tag(self) -> str:
        """Effective release tag: the env override if set, else APP_VERSION."""
        return self.hkcc_release_tag or APP_VERSION


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
    if settings.release_tag == "dev":
        return ["*"]
    return []
