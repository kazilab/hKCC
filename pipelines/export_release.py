"""Export versioned dataset snapshots (CSV / JSON / Parquet)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from db.models import KCC, Agent, DatasetRelease, Evidence
from db.session import SessionLocal

EXPORT_DIR = Path(__file__).resolve().parents[1] / "exports"


def export_release(tag: str) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = EXPORT_DIR / tag
    out.mkdir(exist_ok=True)
    db = SessionLocal()
    try:
        kccs = pd.read_sql(select(KCC).order_by(KCC.n), db.bind)
        agents = pd.read_sql(select(Agent), db.bind)
        evidence = pd.read_sql(select(Evidence), db.bind)
        kccs.to_csv(out / "kccs.csv", index=False)
        agents.to_csv(out / "agents.csv", index=False)
        evidence.to_csv(out / "evidence.csv", index=False)
        kccs.to_parquet(out / "kccs.parquet", index=False)
        agents.to_parquet(out / "agents.parquet", index=False)
        evidence.to_parquet(out / "evidence.parquet", index=False)
        manifest = {
            "tag": tag,
            "exported_at": datetime.now(UTC).isoformat(),
            "license": "CC-BY-4.0",
            "files": ["kccs", "agents", "evidence"],
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        db.merge(DatasetRelease(tag=tag, notes="Automated export"))
        db.commit()
    finally:
        db.close()
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    path = export_release(args.tag)
    print(f"Exported to {path}")


if __name__ == "__main__":
    main()
