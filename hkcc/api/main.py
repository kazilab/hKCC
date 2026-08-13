from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hkcc.api.observability import init_sentry
from hkcc.api.routers import (
    agents,
    assays,
    contribute,
    domains,
    kccs,
    matrix,
    methodology,
    monograph,
)
from hkcc.db.config import APP_CONTACT_EMAIL, APP_DEVELOPER, APP_TITLE, APP_VERSION, allowed_origins, get_settings

init_sentry("api")

settings = get_settings()

# Heal an older SQLite DB to the current model before serving.
# See db.session.ensure_sqlite_schema.
from hkcc.db.session import ensure_sqlite_schema  # noqa: E402

ensure_sqlite_schema()

app = FastAPI(
    title="hKCC API",
    description=f"{APP_TITLE} read API (v1)",
    version=APP_VERSION,
    contact={"name": APP_DEVELOPER, "email": APP_CONTACT_EMAIL},
    license_info={"name": "MIT"},
)

_origins = allowed_origins()
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

prefix = "/api/v1"
app.include_router(kccs.router, prefix=prefix)
app.include_router(domains.router, prefix=prefix)
app.include_router(agents.router, prefix=prefix)
app.include_router(matrix.router, prefix=prefix)
app.include_router(assays.router, prefix=prefix)
app.include_router(methodology.router, prefix=prefix)
app.include_router(monograph.router, prefix=prefix)
app.include_router(contribute.router, prefix=prefix)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness **and** readiness.

    This returned "ok" from the process alone, so a deployment whose database
    was missing or unreadable reported healthy while every data endpoint failed
    — and the Streamlit client uses this probe to decide whether the API is
    usable, so it would route reads to a backend that cannot serve them.
    """
    from sqlalchemy import select

    from hkcc.db.models import KCC
    from hkcc.db.session import SessionLocal

    body = {"status": "ok", "release": settings.release_tag, "database": "ok"}
    try:
        db = SessionLocal()
        try:
            db.execute(select(KCC.id).limit(1)).first()
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 — any failure means "not ready"
        body["status"] = "degraded"
        body["database"] = f"unavailable: {type(exc).__name__}"
        return JSONResponse(status_code=503, content=body)
    return body
