# hKCC - Scope decisions

Decisions locked for implementation (do not re-litigate without explicit change request).

| Field | Value |
|-------|-------|
| **Version** | see [`pyproject.toml`](../pyproject.toml) |
| **Developed by** | Data Analysis Team @KaziLab.se |
| **Contact** | hkcc@kazilab.se |

| Topic | Decision |
|-------|----------|
| **Initial dataset** | Reference-backed SQLite database (`hkcc.db`), committed to the repository: KCC framework definitions, KCAD, IARC 10-year retrospective matrix, and foundational references. |
| **Distribution** | The database ships with the code. There is no build, migration or seed step at install or deploy time; the one-off importers that produced `hkcc.db` from the published supplementary files are not part of the distribution. |
| **Deployment** | Streamlit Community Cloud reading the bundled `hkcc.db`, plus a PyPI distribution. No container scaffolding is maintained. |
| **Annotation model** | Two layers: the ten established KCCs are the reference ontology and the only scored layer; cross-cutting candidate domains (EMD1–4 from Kazi et al., plus CD5) parent onto them and never score independently. |
| **Curator workflow** | **v2.** Schema includes `curators` + `revisions`; no authenticated curator UI in current version. |
| **Repository layout** | Single `hkcc/` package (`hkcc/app/`, `hkcc/api/`, `hkcc/db/`, `hkcc/pipelines/`, `data/`), with `tests/` and `docs/` at the repo root. |

## Non-negotiables (foundation)

- Evidence scores link to citations at the cell level (`evidence_citations`).
- Dataset releases tagged; export CSV/JSON/Parquet; Zenodo archive hook in `hkcc/pipelines/export_release.py`.
- Licensing: data CC-BY-4.0, code MIT — footer + README.
- BibTeX/RIS generation for resource and agent profiles (`api` + `app` utilities).
- pytest for API; Streamlit page smoke tests.
- GitHub Actions: lint, tests.

## Build order (this repo)

1. Scaffold + SQLAlchemy schema (`hkcc/db/models.py` is the single schema source of truth)
2. KCC framework definitions stored in `hkcc.db`
3. FastAPI (5 route groups)
4. Streamlit: Overview + Browse KCCs → Carcinogens → Matrix → remaining pages
5. PyPI distribution (`pip install hkcc`) + Streamlit Cloud deployment
