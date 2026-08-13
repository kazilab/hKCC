# hKCC - Key Characteristics of Human Carcinogens

An open database mapping mechanistic evidence from carcinogenic agents to the ten Key Characteristics (KCC) framework, with a second layer of cross-cutting candidate domains.

> **Status: early development (v0.0.x).** The dataset, the schema and the API are all
> still changing between releases. Scores are derived from published source tables by
> the documented rules in [`docs/KCC_EVIDENCE_RULES.md`](docs/KCC_EVIDENCE_RULES.md) —
> read them before relying on a value.

| Layer | Stack |
|-------|--------|
| Frontend | Streamlit (multi-page, sidebar nav) |
| API | FastAPI `/api/v1/*` |
| Database | SQLite (`hkcc.db`, ships inside the package), SQLAlchemy |
| Pipelines | Python (`hkcc/pipelines/`) |

**Live app:** <https://hu-kcc.streamlit.app/>  
**Version:** defined once in [`pyproject.toml`](pyproject.toml) (`[project].version`)  
**Developed by:** Data Analysis Team @KaziLab.se  
**Contact:** hkcc@kazilab.se  
**Licenses:** data [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) · code MIT

The version is the single source of truth in `pyproject.toml`; `hkcc/db/config.py` derives
`APP_VERSION` from it (and exposes `APP_DEVELOPER`, `APP_CONTACT_EMAIL`). Nothing else
hardcodes the version — bump it in one place.

Documentation: [scope decisions](docs/SCOPE.md) · [database tables](docs/DATABASE_TABLES.md) · [evidence rules](docs/KCC_EVIDENCE_RULES.md)

## Install

Try it first at **<https://hu-kcc.streamlit.app/>** — nothing to install.

To run it yourself:

```bash
pip install hkcc
hkcc            # Streamlit app on :8501
hkcc api        # read API on :8000/docs
hkcc info       # version + dataset location
```

The dataset ships inside the package — `pip install hkcc` gives you all ten KCCs,
171 agents, 844 evidence cells, 573 assays, 1,171 references and the IARC
Monograph matrix, with no build step, no database server and no `.env` file.

**Coverage.** The mechanistic evidence derives from two published sources: the
IARC Monograph **Volume 100** Group 1 re-review (Krewski et al. 2019) and
**Volumes 112–130** (Rusyn et al. 2024). Each score records which source produced
it, and the two use different derivation rules — see
[`docs/KCC_EVIDENCE_RULES.md`](docs/KCC_EVIDENCE_RULES.md). Volumes 107–111 are
not covered by either.

**Known limitations.** [`docs/ROADMAP.md`](docs/ROADMAP.md) records the limitations
that are known and deliberate — chiefly that the 0–4 scale carries three different
derivations, and that coverage counts do not yet separate strength from direction
and IARC data role. Read it before using scores comparatively.

## Development

```bash
git clone https://github.com/kazilab/hkcc && cd hkcc
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
streamlit run hkcc/streamlit_app.py   # :8501
uvicorn hkcc.api.main:app --reload    # :8000/docs
pytest
```

To read a different SQLite file, set `DATABASE_URL`:

```bash
export DATABASE_URL="sqlite:////absolute/path/to/hkcc.db"
```

## API (v1)

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/kccs` | The ten established KCCs (reference ontology) |
| `GET /api/v1/domains` | Cross-cutting candidate domains (EMD1–4, CD5) |
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

## Two layers

The ten established KCCs (Smith et al. 2016) are the reference ontology and the only
thing carrying an `evidence.score`. Alongside them sit five **candidate mechanistic
domains** — EMD1–EMD4 from Kazi et al., plus CD5 (gap-junctional communication) as a
platform-level candidate. Domains qualify *how* an observation arose and parent onto one
or more KCCs; they never score independently, so the same experiment cannot be counted
twice. See [`docs/KCC_EVIDENCE_RULES.md`](docs/KCC_EVIDENCE_RULES.md).

## Data sources

Every derived row in `hkcc.db` carries a `source_ref_id` pointing back to the
canonical publication record it came from. Two peer-reviewed datasets underpin
the database.

**KCAD — Key Characteristics Assay Database.** Source of the assay library, the
study-level annotations, the abbreviation glossary and the column dictionary
(`source_ref_id = kcad-paper-rigutto-2025`).

> **Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT.**
> *Mapping assays to the key characteristics of carcinogens to support
> decision-making.* Database (Oxford) **2025**, article `baaf026`.
> DOI: [`10.1093/database/baaf026`](https://doi.org/10.1093/database/baaf026).

**IARC 10-year retrospective.** Source of `iarc_monograph_kc_calls` (per-volume,
per-model-system Yes/No/Equivocal/Protective calls), `iarc_monograph_kc_strength`
(per-(agent, KC) standardized labels) and the derived `evidence` scores
(`source_ref_id = rusyn2024-tenyears`).

> **Rusyn I, Wright FA, Smith MT, et al.** *Ten years of using key
> characteristics of human carcinogens to organize and evaluate mechanistic
> evidence in IARC Monographs Volumes 112–130.* Toxicological Sciences
> 198(1):141–154 (2024).
> DOI: [`10.1093/toxsci/kfad134`](https://doi.org/10.1093/toxsci/kfad134).

See [`docs/KCC_EVIDENCE_RULES.md`](docs/KCC_EVIDENCE_RULES.md) for the algorithm
that maps the published cell labels to the 0–4 `evidence.score` scale, and
[`docs/DATABASE_TABLES.md`](docs/DATABASE_TABLES.md) for a table-by-table account
of which source populated what.

Companion references generated from the database:

- [`docs/KCAD_DATA_DICTIONARY.md`](docs/KCAD_DATA_DICTIONARY.md) — column-by-column
  definitions of the KCAD annotation table.
- [`docs/KCAD_ABBREVIATIONS.md`](docs/KCAD_ABBREVIATIONS.md) — 49 abbreviations
  used in the dataset.

Both are regenerated with `python -m hkcc.pipelines.gen_kcad_docs`.

## Repo layout

```
hkcc/
  app/            Streamlit UI (pages, components, theme)
  api/            FastAPI service
  db/             Models, session, config
  pipelines/      Export, maintenance scripts, external API clients
  data/hkcc.db    The dataset — single source of truth
  cli.py          `hkcc` console entry point
  streamlit_app.py
tests/            pytest
docs/             Scope & architecture notes
```

`hkcc/data/hkcc.db` is the only place data lives. There are no seed files
mirroring its contents, so nothing can drift out of sync with it.
`docs/KCAD_DATA_DICTIONARY.md` and `docs/KCAD_ABBREVIATIONS.md` are generated
*from* the database:

```bash
python -m hkcc.pipelines.gen_kcad_docs
```

## Dataset releases

```bash
python -m hkcc.pipelines.export_release   # --tag defaults to the pyproject.toml version
```

Exports land in `exports/<tag>/` under the repo root (or the working directory
when running from an installed package; `HKCC_EXPORT_DIR` overrides both) as
CSV, a JSON manifest and Parquet. Archive to Zenodo manually until DOI automation lands.
