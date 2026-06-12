from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.observability import init_sentry
from api.routers import agents, assays, contribute, kccs, matrix, methodology, monograph
from db.config import APP_CONTACT_EMAIL, APP_DEVELOPER, APP_TITLE, APP_VERSION, allowed_origins, get_settings

init_sentry("api")

settings = get_settings()

# Heal a committed/older SQLite DB to the current model before serving (no-op for
# Postgres / API-remote deploys). See db.session.ensure_sqlite_schema.
from db.session import ensure_sqlite_schema  # noqa: E402

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
app.include_router(agents.router, prefix=prefix)
app.include_router(matrix.router, prefix=prefix)
app.include_router(assays.router, prefix=prefix)
app.include_router(methodology.router, prefix=prefix)
app.include_router(monograph.router, prefix=prefix)
app.include_router(contribute.router, prefix=prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "release": settings.release_tag}
