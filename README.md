# hKCC — Key Characteristics of Human Carcinogens

Production platform for mapping mechanistic evidence linking carcinogenic agents to the 14 Key Characteristics (KCC) framework.

| Layer | Stack |
|-------|--------|
| Frontend | Streamlit (multi-page, sidebar nav) |
| API | FastAPI `/api/v1/*` |
| Database | SQLite by default, PostgreSQL 16 optional, SQLAlchemy |
| Pipelines | Python (`pipelines/`) |

**Licenses:** data [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) · code MIT

Scope decisions: [docs/SCOPE.md](docs/SCOPE.md)

The JSX/HTML mockup in this repo root is **design reference only** — not ported source.

## Quick start

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m db.bootstrap_sqlite --replace
streamlit run streamlit_app.py  # :8501
uvicorn api.main:app --reload   # :8000/docs, optional
pytest
```

The default local backend is a single SQLite file (`hkcc.db`), which is enough
for read-only browsing and local API use. The SQLite bootstrap is
reference-backed: it seeds only the KCC framework definitions, then imports
KCAD and IARC data. PostgreSQL remains supported for production or multi-user
deployments:

```bash
cd infra && docker compose up -d db
cd ..
cp .env.example .env
# edit .env so DATABASE_URL=postgresql+psycopg://hkcc:hkcc@localhost:5432/hkcc
alembic -c db/alembic.ini upgrade head
python -m db.seed.load_seed
python -m pipelines.import_kcad --with-supplementary --reset-kcad
python -m pipelines.import_10yr_kcc
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
| `GET /api/v1/monograph/volumes` | IARC Monograph volumes covered by the 10-yr matrix |
| `GET /api/v1/monograph/calls` | Per-(volume, agent, model-system, KC) call rows |
| `GET /api/v1/monograph/strengths` | Per-(agent, KC) standardized strength labels |
| `GET /api/v1/monograph/agent/{id}` | Heat-map shape for a single agent |
| `GET /api/v1/monograph/kcc/{id}` | Agents with a given call for a given KC |
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

## IARC 10-year retrospective integration

The Rusyn et al. 2024 supplementary tables (`references/kcc-10yr/`) are
ingested into two paper-authoritative tables — `iarc_monograph_kc_calls`
(per-volume, per-model-system Yes/No/Equivocal/Protective calls) and
`iarc_monograph_kc_strength` (per-(agent, KC) standardized Strong/Moderate/
Weak labels). Both anchor to a canonical Reference row
`rusyn2024-tenyears` (DOI [`10.1093/toxsci/kfad134`](https://doi.org/10.1093/toxsci/kfad134))
that also points to the local PDF copy.

> **Rusyn I, Wright FA, Smith MT, et al.** *Ten years of using key
> characteristics of human carcinogens to organize and evaluate mechanistic
> evidence in IARC Monographs Volumes 112–130.* Toxicological Sciences
> 198(1):141–154 (2024).

```bash
python -m pipelines.import_10yr_kcc
```

The importer also seeds 15 foundational references from
`db/seed/refs/foundational.json` (Smith 2016, Guyton 2018, Smith 2020,
Rieswijk 2019, Tcheremenskaia 2021, …) — every entry carries a DOI/URL plus a
`pdf_path` so the **About → Methodology** page can hyperlink directly to the
PDF in `references/`. See [`docs/KCC_EVIDENCE_RULES.md`](docs/KCC_EVIDENCE_RULES.md)
for the deterministic algorithm that maps the paper's cell labels to the
0–4 `evidence.score` scale.

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
