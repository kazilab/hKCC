# Deploy guide (v1)

## Local (Docker Compose)

```bash
cd infra
docker compose up -d db
export DATABASE_URL=postgresql+psycopg://hkcc:hkcc@localhost:5432/hkcc
pip install -e ".[dev]"
alembic -c db/alembic.ini upgrade head
python -m db.seed.load_seed --reset
docker compose up api app
```

- API: http://localhost:8000/docs
- App: http://localhost:8501

## Streamlit Community Cloud + Supabase

1. Create a Supabase project (PostgreSQL 16). Copy the connection string.
2. Run migrations and seed from your machine:

   ```bash
   export DATABASE_URL="postgresql+psycopg://..."
   alembic -c db/alembic.ini upgrade head
   python -m db.seed.load_seed --reset
   ```

3. Deploy API (Railway, Fly.io, or Render) with `DATABASE_URL` and `HKCC_RELEASE_TAG`.
4. Deploy Streamlit app; set secrets (see `.streamlit/secrets.toml.example`):
   - `DATABASE_URL` — required for live curated data
   - `API_BASE_URL` — optional; if healthy, API takes priority over the DB

   **Without secrets**, the app runs in **demo mode** using bundled `data.js` (no Postgres needed).

5. Tag releases: `python -m pipelines.export_release --tag 0.1.0` then upload `exports/` to Zenodo.

## Self-hosted

Use `infra/docker-compose.yml` on a VM with TLS termination (Caddy/nginx). Point DNS at the Streamlit and API services.
