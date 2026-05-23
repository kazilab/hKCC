from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.observability import init_sentry
from api.routers import agents, assays, contribute, kccs, matrix, methodology
from db.config import allowed_origins, get_settings

init_sentry("api")

settings = get_settings()

app = FastAPI(
    title="hKCC API",
    description="Key Characteristics of Human Carcinogens — read API (v1)",
    version="0.1.0",
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
app.include_router(contribute.router, prefix=prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "release": settings.hkcc_release_tag}
