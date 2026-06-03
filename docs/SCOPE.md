# hKCC v1 — Scope decisions

Decisions locked for implementation (do not re-litigate without explicit change request).

| Topic | Decision |
|-------|----------|
| **Initial dataset** | Reference-backed SQLite/PostgreSQL seed: KCC framework definitions, KCAD, IARC 10-year retrospective matrix, and foundational references. |
| **Deployment (v1)** | Streamlit Community Cloud + Supabase PostgreSQL free tier. `infra/` documents self-hosted Docker path for local dev and future migration. |
| **Curator workflow** | **v2.** Schema includes `curators` + `revisions`; no authenticated curator UI in v1. |
| **Public API** | **Live in v1** — read-only FastAPI at `/api/v1/*`. `POST /contribute` accepts proposals (stored, not applied) for v2 review. |
| **ORCID auth** | **v2** for curator/researcher tiers. v1 is anonymous read-only Streamlit + API. |
| **Repository layout** | **Monorepo:** `app/`, `api/`, `db/`, `pipelines/`, `infra/`, `tests/`, `docs/`. |

## Non-negotiables (v1 foundation)

- Evidence scores link to citations at the cell level (`evidence_citations`).
- Dataset releases tagged; export CSV/JSON/Parquet; Zenodo archive hook in `pipelines/export_release.py`.
- Licensing: data CC-BY-4.0, code MIT — footer + README.
- BibTeX/RIS generation for resource and agent profiles (`api` + `app` utilities).
- pytest for API; Streamlit page smoke tests.
- GitHub Actions: lint, tests, `alembic upgrade head` check.

## Build order (this repo)

1. Scaffold + Postgres + Alembic schema
2. Seed KCC framework definitions from `db/seed/kccs.json`
3. FastAPI (5 route groups)
4. Streamlit: Overview + Browse KCCs → Carcinogens → Matrix → remaining pages
5. Docker Compose + deploy guide
