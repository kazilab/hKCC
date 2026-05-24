#!/bin/sh
# API container entrypoint: run migrations, then exec uvicorn.
set -eu

if [ "${HKCC_RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic -c db/alembic.ini upgrade head
fi

if [ "${HKCC_RUN_SEED:-0}" = "1" ]; then
  echo "[entrypoint] seeding (HKCC_RUN_SEED=1)"
  python -m db.seed.load_seed --reset
fi

exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --proxy-headers
