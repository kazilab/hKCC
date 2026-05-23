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
| `GET /api/v1/agents/{id}/references` | KCAD references linked to an agent |
| `GET /api/v1/matrix` | Evidence matrix |
| `GET /api/v1/assays` | Assay library (filters: `source`, `design`, `subgroup`) |
| `GET /api/v1/assays/{id}` | Single assay (includes KC subgroups + study designs) |
| `GET /api/v1/assays/{id}/annotations` | Study-level annotations for an assay |
| `GET /api/v1/assays/references` | Literature |
| `GET /api/v1/methodology/source` | KCAD source paper (Rigutto et al. 2025) |
| `GET /api/v1/methodology/abbreviations` | KCAD abbreviations glossary (49 entries) |
| `GET /api/v1/methodology/columns` | KCAD column data dictionary (28 entries) |
| `POST /api/v1/contribute` | Submit score proposal (queued for v2 curation) |

## KCAD data integration

The Key Characteristics Assay Database (**KCAD**) data shipped in
`suppl_data/` is fully integrated. Every KCAD-derived row in the database
carries a `source_ref_id` pointing back to the canonical publication record:

> **Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT.**
> *Mapping assays to the key characteristics of carcinogens to support
> decision-making.* Database (Oxford) **2025**, article `baaf026`.
> DOI: [`10.1093/database/baaf026`](https://doi.org/10.1093/database/baaf026).

Companion docs:

- [`docs/KCAD_DATA_DICTIONARY.md`](docs/KCAD_DATA_DICTIONARY.md) — column-by-column
  definitions of `filtered_table.csv` (auto-generated from STable2).
- [`docs/KCAD_ABBREVIATIONS.md`](docs/KCAD_ABBREVIATIONS.md) — 49 abbreviations
  used in the dataset (auto-generated from STable3).

Run the full importer once Postgres + Alembic are up:

```bash
python -m pipelines.import_kcad --with-supplementary --reset-kcad
# or, equivalently, two separate calls:
python -m pipelines.import_kcad --reset-kcad
python -m pipelines.import_kcad_supplementary
```

## Repo layout

```
app/          Streamlit UI
api/          FastAPI service
db/           Models, Alembic, seed
pipelines/    Export, external API clients (`pipelines/clients/`), batch stubs
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
- [x] Live feed UI (PubChem, PubChem assay summary / screening bridge, OpenAlex, CompTox links + optional CCTE key)
