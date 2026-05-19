# hKCC — Key Characteristics of Human Carcinogens

Production platform for mapping mechanistic evidence linking carcinogenic agents to the 14 Key Characteristics (KCC) framework.

| Layer | Stack |
|-------|--------|
| Frontend | Streamlit (multi-page, sidebar nav) |
| API | FastAPI `/api/v1/*` |
| Database | PostgreSQL 16, SQLAlchemy, Alembic |
| Pipelines | Python (`pipelines/`) |

**Licenses:** data [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) · code MIT

Scope decisions: [docs/SCOPE.md](docs/SCOPE.md)

The JSX/HTML mockup in this repo root is **design reference only** — not ported source.

## Quick start

```bash
cd infra && docker compose up -d db
cd ..
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic -c db/alembic.ini upgrade head
python -m db.seed.load_seed --reset
uvicorn api.main:app --reload   # :8000/docs
streamlit run streamlit_app.py  # :8501
pytest
```

## API (v1)

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/kccs` | List KCCs |
| `GET /api/v1/agents` | List agents |
| `GET /api/v1/matrix` | Evidence matrix |
| `GET /api/v1/assays` | Assay library |
| `GET /api/v1/assays/references` | Literature |
| `POST /api/v1/contribute` | Submit score proposal (queued for v2 curation) |

## Repo layout

```
app/          Streamlit UI
api/          FastAPI service
db/           Models, Alembic, seed
pipelines/    Export + external sync stubs
infra/        Docker Compose, deploy guide
tests/        pytest
docs/         Scope & architecture notes
```

## Dataset releases

```bash
python -m pipelines.export_release --tag 0.1.0
```

Exports land in `exports/<tag>/` (CSV, JSON manifest, Parquet). Archive to Zenodo manually until DOI automation lands.

## Roadmap (from project brief)

- [x] Schema + seed + API + all Streamlit pages (Overview → About)
- [x] Evidence matrix heatmap (`st.components.html`)
- [x] Agent radar plot (`st.components.html`)
- [ ] ORCID curator UI (v2)
- [ ] Live PubChem / ToxCast / OpenAlex pipelines
