"""Export versioned dataset snapshots (CSV / JSON / Parquet)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from sqlalchemy import select

from db.models import (
    KCC,
    Agent,
    AgentReference,
    Assay,
    AssayAnnotation,
    AssayKCC,
    AssayKcSubgroup,
    AssayStudyDesign,
    DatasetRelease,
    Evidence,
    IarcMonographKcCall,
    IarcMonographKcStrength,
    KcadAbbreviation,
    KcadColumnDefinition,
    Reference,
)
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
        assays = pd.read_sql(select(Assay), db.bind)
        assay_kccs = pd.read_sql(select(AssayKCC), db.bind)
        references = pd.read_sql(select(Reference), db.bind)
        agent_references = pd.read_sql(select(AgentReference), db.bind)
        assay_annotations = pd.read_sql(select(AssayAnnotation), db.bind)
        assay_kc_subgroups = pd.read_sql(select(AssayKcSubgroup), db.bind)
        assay_study_designs = pd.read_sql(select(AssayStudyDesign), db.bind)
        kcad_abbreviations = pd.read_sql(select(KcadAbbreviation), db.bind)
        kcad_column_definitions = pd.read_sql(select(KcadColumnDefinition), db.bind)
        iarc_monograph_kc_calls = pd.read_sql(select(IarcMonographKcCall), db.bind)
        iarc_monograph_kc_strength = pd.read_sql(select(IarcMonographKcStrength), db.bind)

        tables: dict[str, pd.DataFrame] = {
            "kccs": kccs,
            "agents": agents,
            "evidence": evidence,
            "assays": assays,
            "assay_kccs": assay_kccs,
            "references": references,
            "agent_references": agent_references,
            "assay_annotations": assay_annotations,
            "assay_kc_subgroups": assay_kc_subgroups,
            "assay_study_designs": assay_study_designs,
            "kcad_abbreviations": kcad_abbreviations,
            "kcad_column_definitions": kcad_column_definitions,
            "iarc_monograph_kc_calls": iarc_monograph_kc_calls,
            "iarc_monograph_kc_strength": iarc_monograph_kc_strength,
        }
        csv_files = [f"{name}.csv" for name in tables]
        parquet_files = [f"{name}.parquet" for name in tables]
        for name, df in tables.items():
            df.to_csv(out / f"{name}.csv", index=False)
            df.to_parquet(out / f"{name}.parquet", index=False)

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
                    **{name: _records(df) for name, df in tables.items()},
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
