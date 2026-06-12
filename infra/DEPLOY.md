# Deploy guide

Developed by: Data Analysis Team @KaziLab.se  
Contact: hkcc@kazilab.se

## Local (Docker Compose)

```bash
cd infra
docker compose up -d db
docker compose up --build api app
```

On first boot the API container runs `alembic upgrade head` automatically. To
also load the KCC framework seed inside the container, set `HKCC_RUN_SEED=1`
for the first run, then remove it:

```bash
HKCC_RUN_SEED=1 docker compose up --build api
```

- API: <http://localhost:8000/docs>
- App: <http://localhost:8501>

## Streamlit Community Cloud + Supabase

1. Create a Supabase project (PostgreSQL 16). Copy the connection string.
2. Run migrations and seed from your machine:

   ```bash
   export DATABASE_URL="postgresql+psycopg://..."
   alembic -c db/alembic.ini upgrade head
   python -m db.seed.load_seed --reset
   ```

3. Deploy API (Railway, Fly.io, or Render). Required env vars:
   - `DATABASE_URL`
   - `HKCC_RELEASE_TAG` (optional — defaults to the `pyproject.toml` version; set only to override)
   - `HKCC_ALLOWED_ORIGINS` (comma-separated; **required** outside dev — leave empty in non-dev to disable CORS)
   - Optional: `HKCC_CONTRIBUTE_MAX_PER_WINDOW`, `HKCC_CONTRIBUTE_WINDOW_SECONDS`
   - Optional: `SENTRY_DSN`
4. Deploy Streamlit app; set secrets:
   - `DATABASE_URL` — required for live curated data
   - `API_BASE_URL` — optional; if healthy, API takes priority over the DB
   - `OPENALEX_MAILTO` — required for the live OpenAlex pool in production
   - Optional: `EPA_CCTE_API_KEY`, `SENTRY_DSN`

   **Without secrets**, the app uses the bundled SQLite database (`hkcc.db`)
   when present. No Postgres service is required for read-only browsing.

5. Tag releases:

   ```bash
   python -m pipelines.export_release   # --tag defaults to the pyproject.toml version
   ```

   Then upload `exports/<tag>/` to Zenodo (manual until DOI automation lands).

## Self-hosted

Use `infra/docker-compose.yml` on a VM with TLS termination (Caddy/nginx).
Point DNS at the Streamlit and API services. Recommended baseline:

- TLS via Caddy or Cloudflare; set `HKCC_ALLOWED_ORIGINS` to your public app
  origin(s) only.
- Reverse proxy should set `X-Forwarded-For`; the API's in-process rate limit
  honours the first hop of that header.
- Daily logical backup of the database (`pg_dump | gzip > …`) plus a weekly
  restore drill.
- Schedule `pipelines/export_release.py` to drop a fresh snapshot to object
  storage for citable releases.

## Operational env reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | Postgres URL used by API + Streamlit fallback | local Postgres |
| `API_BASE_URL` | When set & healthy, Streamlit prefers the API over the DB | `http://localhost:8000` |
| `HKCC_RELEASE_TAG` | Version stamp used in citations, exports, `/health` | `pyproject.toml` version |
| `HKCC_ALLOWED_ORIGINS` | Comma-separated CORS allowlist | empty (closed unless tag == `dev`) |
| `HKCC_CONTRIBUTE_MAX_PER_WINDOW` | `POST /contribute` cap per client IP | `10` |
| `HKCC_CONTRIBUTE_WINDOW_SECONDS` | Sliding window length, seconds | `3600` |
| `HKCC_RUN_MIGRATIONS` | API entrypoint runs `alembic upgrade head` | `1` |
| `HKCC_RUN_SEED` | API entrypoint re-runs the KCC framework seed | `0` |
| `OPENALEX_MAILTO` | OpenAlex polite-pool email | `hkcc@kazilab.se` |
| `EPA_CCTE_API_KEY` | Optional EPA CCTE key | empty |
| `SENTRY_DSN` | Optional Sentry DSN (API + Streamlit) | empty |
