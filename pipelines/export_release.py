"""Export versioned dataset snapshots (CSV / JSON / Parquet)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from sqlalchemy import select

from db.models import KCC, Agent, DatasetRelease, Evidence
from db.session import SessionLocal

EXPORT_DIR = Path(__file__).resolve().parents[1] / "exports"


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _zip_files(out: Path, archive_name: str, files: list[str]) -> None:
    with ZipFile(out / archive_name, "w", ZIP_DEFLATED) as zf:
        for fname in files:
            path = out / fname
            if path.is_file():
                zf.write(path, arcname=fname)


def export_release(tag: str) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = EXPORT_DIR / tag
    out.mkdir(exist_ok=True)
    db = SessionLocal()
    try:
        kccs = pd.read_sql(select(KCC).order_by(KCC.n), db.bind)
        agents = pd.read_sql(select(Agent), db.bind)
        evidence = pd.read_sql(select(Evidence), db.bind)
        csv_files = ["kccs.csv", "agents.csv", "evidence.csv"]
        parquet_files = ["kccs.parquet", "agents.parquet", "evidence.parquet"]
        for df, fname in zip((kccs, agents, evidence), csv_files):
            df.to_csv(out / fname, index=False)
        for df, fname in zip((kccs, agents, evidence), parquet_files):
            df.to_parquet(out / fname, index=False)

        exported_at = datetime.now(UTC).isoformat()
        json_file = f"hkcc-{tag}.json"
        csv_bundle = f"hkcc-{tag}.csv.zip"
        parquet_bundle = f"hkcc-{tag}.parquet.zip"
        (out / json_file).write_text(
            json.dumps(
                {
                    "tag": tag,
                    "exported_at": exported_at,
                    "license": "CC-BY-4.0",
                    "kccs": _records(kccs),
                    "agents": _records(agents),
                    "evidence": _records(evidence),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        _zip_files(out, csv_bundle, csv_files)
        _zip_files(out, parquet_bundle, parquet_files)

        manifest = {
            "tag": tag,
            "exported_at": exported_at,
            "license": "CC-BY-4.0",
            "files": [csv_bundle, json_file, parquet_bundle, *csv_files, *parquet_files],
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
