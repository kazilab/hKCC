# hKCC — standalone single-file build

A **read-only, fully offline** build of the hKCC atlas as one self-contained
`index.html` (React + TypeScript, bundled with Vite). All data is embedded — no
backend, no database, no network requests. Intended as a citable, archival
artifact (e.g. a Zenodo upload alongside a release DOI).

This is an **additional** distribution. It does not change the live Streamlit /
FastAPI application in `app/`, `api/`, `db/`, `pipelines/` — it only *reads* the
same `hkcc.db`.

## What's included
Overview, the carcinogen × KCC evidence **Matrix**, **Carcinogens** (search +
per-agent evidence and linked literature), **KCCs** (with linked agents/assays/
references), the **Assay** library, **Methodology** (KCAD glossary + column
dictionary), and **About** with BibTeX/RIS citation export. The score-proposal
(`/contribute`) write path is replaced by an email link, since a static bundle
has no backend.

## Build
Requires Node 18+ and Python 3.11+ (stdlib only — no project deps needed).

```bash
cd standalone
npm install
npm run build        # regenerates data, type-checks, emits dist/index.html
```

Open `dist/index.html` directly in any browser (file:// works), or `npm run dev`
for live development. The data step alone:

```bash
npm run export-data  # reads ../hkcc.db -> src/data.json
```

## How the version stays single-sourced
`scripts/export_data.py` reads the version from the repo's `pyproject.toml`
(the single source of truth), so the bundle's footer/About show the same version
as the main app without a second place to edit.

## Data freshness
`src/data.json` is regenerated from `../hkcc.db` on every `npm run build` /
`npm run dev` (via the `prebuild`/`predev` hooks). Rebuild after re-importing or
re-curating data to refresh the bundle.

## Not included vs. the live app
Per-study assay annotations (the ~20k-row `assay_annotations` detail) are omitted
to keep the single file lightweight; everything else mirrors the Streamlit views.
Add them in `scripts/export_data.py` + `AssayDetail.tsx` if needed.
