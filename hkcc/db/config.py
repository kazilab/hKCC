from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root of the installed ``hkcc`` package (``.../site-packages/hkcc`` when
# installed, ``<repo>/hkcc`` in a checkout). The dataset ships inside it.
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = PACKAGE_ROOT / "data" / "hkcc.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

# Repo root when running from a source checkout; ``None`` once installed.
REPO_ROOT = PACKAGE_ROOT.parent if (PACKAGE_ROOT.parent / "pyproject.toml").is_file() else None
_REPO_ROOT = REPO_ROOT


def export_dir() -> Path:
    """Where dataset export bundles are written.

    Never inside the installed package: exports are writable output. From a
    source checkout they land in ``<repo>/exports``; from an installed package,
    in ``./exports`` under the working directory. ``HKCC_EXPORT_DIR`` overrides
    both.
    """
    import os

    override = os.environ.get("HKCC_EXPORT_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return (REPO_ROOT or Path.cwd()) / "exports"


def _resolve_version() -> str:
    """Single source of truth for the app version is ``pyproject.toml``.

    In a source checkout we parse ``pyproject.toml`` directly, so bumping that
    one number takes effect immediately (no reinstall needed). In an installed
    package — where ``pyproject.toml`` isn't shipped — we read the distribution
    metadata. Either way the version is never duplicated in code.
    """
    if _REPO_ROOT is not None:
        import tomllib

        with (_REPO_ROOT / "pyproject.toml").open("rb") as fh:
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

# Canonical `references.id` anchors for the two published source datasets every
# derived row points back to via `source_ref_id`. Kept here (not in a pipeline)
# because the API and the Streamlit app both resolve them at read time.
KCAD_PAPER_REF_ID = "kcad-paper-rigutto-2025"  # Rigutto et al. 2025, 10.1093/database/baaf026
KCC10YR_REF_ID = "rusyn2024-tenyears"  # Rusyn et al. 2024, 10.1093/toxsci/kfad134
VOL100_REF_ID = "krewski2019-iarcsp165-ch22"  # Krewski et al. 2019, IARC Sci. Pub. 165 Ch. 22
VOL100_DB_REF_ID = "rieswijk2019-firstdb"  # Al-Zoughool et al. 2019, 10.1080/10937404.2019.1642593

# The published analyses scores are *computed from*. A cell citing one of these
# is citing its derivation, not a primary mechanistic study — true for 775 of
# the 844 evidence cells, so the UI must not present them as source experiments.
DERIVATION_REF_IDS = frozenset({KCC10YR_REF_ID, VOL100_REF_ID, VOL100_DB_REF_ID})

# Agents that merge exposures IARC evaluated separately. Rusyn et al. 2024 rows
# arrive as one unit, so hKCC holds one agent and one group where IARC issued
# two. Splitting them changes agent ids and breaks citations, so v0 states the
# discrepancy on the agent page; the split is tracked in docs/ROADMAP.md.
COMBINED_EXPOSURES: dict[str, str] = {
    "red-and-processed-meat": (
        "IARC evaluated these separately: **processed meat is Group 1** and **red meat is "
        "Group 2A**. This row carries one group for both, so the classification shown here "
        "is not what IARC concluded for either component. The mechanistic evidence below is "
        "as published for the combined entry."
    ),
    "drinking-mate-and-very-hot-beverages": (
        "IARC evaluated these separately: **drinking very hot beverages (above 65 °C) is "
        "Group 2A**, while **maté not drunk very hot is Group 3** (not classifiable). This "
        "row carries one group for both, so the classification shown here is not what IARC "
        "concluded for maté at ordinary temperatures."
    ),
}


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
