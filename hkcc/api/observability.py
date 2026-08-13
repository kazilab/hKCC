"""Optional Sentry init.

This module is imported by both the FastAPI service and the Streamlit
entrypoint. It is intentionally dependency-free: ``sentry-sdk`` is **not** a
required project dependency. Operators who want error reporting install
``sentry-sdk`` in the deployed image and set ``SENTRY_DSN`` — everything else
just works.

When either the env var is missing or the SDK isn't installed, ``init_sentry``
is a no-op and returns ``False``.
"""

from __future__ import annotations

import os

from hkcc.db.config import get_settings

_INITIALISED = False


def init_sentry(component: str) -> bool:
    """Initialise Sentry once per process. Returns True if it actually fired."""
    global _INITIALISED
    if _INITIALISED:
        return True
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return False
    release_tag = get_settings().release_tag
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
        environment=release_tag,
        release=release_tag,
    )
    sentry_sdk.set_tag("component", component)
    _INITIALISED = True
    return True
