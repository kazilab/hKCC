"""Export versioned dataset snapshots (CSV / JSON / Parquet)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from sqlalchemy import select

from hkcc.db.config import APP_VERSION, export_dir
from hkcc.db.models import (
    KCC,
    Agent,
    AgentReference,
    AgentSite,
    AnnotationReference,
    Assay,
    AssayAnnotation,
    AssayKCC,
    AssayKcSubgroup,
    AssayStudyDesign,
    CandidateDomain,
    CandidateDomainAssay,
    CandidateDomainKCC,
    CandidateDomainReference,
    CandidateDomainValidationExample,
    DatasetRelease,
    Evidence,
    EvidenceCitation,
    IarcMonographKcCall,
    IarcMonographKcStrength,
    KcadAbbreviation,
    KcadColumnDefinition,
    Reference,
    ReferenceIdentifier,
    ReferenceKCC,
    ReferenceTag,
)
from hkcc.db.session import SessionLocal

# Resolved lazily via db.config.export_dir() so exports never land inside an
# installed package.


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _zip_files(out: Path, archive_name: str, files: list[str]) -> None:
    with ZipFile(out / archive_name, "w", ZIP_DEFLATED) as zf:
        for fname in files:
            path = out / fname
            if path.is_file():
                zf.write(path, arcname=fname)


def _sha256(path: Path) -> str:
    """Checksum of one exported file, streamed so large bundles stay cheap."""
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_release(tag: str) -> Path:
    base = export_dir()
    base.mkdir(parents=True, exist_ok=True)
    out = base / tag
    out.mkdir(exist_ok=True)
    db = SessionLocal()
    try:
        kccs = pd.read_sql(select(KCC).order_by(KCC.n), db.bind)
        agents = pd.read_sql(select(Agent), db.bind)
        evidence = pd.read_sql(select(Evidence), db.bind)
        # The cell-level citation links are the point of the dataset: without
        # them a downloaded release cannot show which reference supports which
        # score. They were previously omitted from every export.
        evidence_citations = pd.read_sql(select(EvidenceCitation), db.bind)
        assays = pd.read_sql(select(Assay), db.bind)
        assay_kccs = pd.read_sql(select(AssayKCC), db.bind)
        references = pd.read_sql(select(Reference), db.bind)
        reference_tags = pd.read_sql(select(ReferenceTag), db.bind)
        reference_kccs = pd.read_sql(select(ReferenceKCC), db.bind)
        reference_identifiers = pd.read_sql(select(ReferenceIdentifier), db.bind)
        agent_sites = pd.read_sql(select(AgentSite), db.bind)
        agent_references = pd.read_sql(select(AgentReference), db.bind)
        assay_annotations = pd.read_sql(select(AssayAnnotation), db.bind)
        annotation_references = pd.read_sql(select(AnnotationReference), db.bind)
        assay_kc_subgroups = pd.read_sql(select(AssayKcSubgroup), db.bind)
        assay_study_designs = pd.read_sql(select(AssayStudyDesign), db.bind)
        kcad_abbreviations = pd.read_sql(select(KcadAbbreviation), db.bind)
        kcad_column_definitions = pd.read_sql(select(KcadColumnDefinition), db.bind)
        iarc_monograph_kc_calls = pd.read_sql(select(IarcMonographKcCall), db.bind)
        iarc_monograph_kc_strength = pd.read_sql(select(IarcMonographKcStrength), db.bind)
        # Layer 2. The annotation model is two-layer -- ten scored KCCs plus
        # cross-cutting candidate domains parented onto them -- but every export
        # shipped Layer 1 only, so a downloaded release could not reconstruct
        # the model it documents.
        candidate_domains = pd.read_sql(select(CandidateDomain), db.bind)
        candidate_domain_kccs = pd.read_sql(select(CandidateDomainKCC), db.bind)
        candidate_domain_assays = pd.read_sql(select(CandidateDomainAssay), db.bind)
        candidate_domain_references = pd.read_sql(select(CandidateDomainReference), db.bind)
        # Non-scoring Layer-2 guidance. Exported so a release carries the rules
        # for reading the domains, not just the domains.
        candidate_domain_validation_examples = pd.read_sql(
            select(CandidateDomainValidationExample), db.bind
        )

        tables: dict[str, pd.DataFrame] = {
            "kccs": kccs,
            "agents": agents,
            "agent_sites": agent_sites,
            "evidence": evidence,
            "evidence_citations": evidence_citations,
            "assays": assays,
            "assay_kccs": assay_kccs,
            "references": references,
            "reference_tags": reference_tags,
            "reference_kccs": reference_kccs,
            "reference_identifiers": reference_identifiers,
            "agent_references": agent_references,
            "assay_annotations": assay_annotations,
            "annotation_references": annotation_references,
            "assay_kc_subgroups": assay_kc_subgroups,
            "assay_study_designs": assay_study_designs,
            "kcad_abbreviations": kcad_abbreviations,
            "kcad_column_definitions": kcad_column_definitions,
            "iarc_monograph_kc_calls": iarc_monograph_kc_calls,
            "iarc_monograph_kc_strength": iarc_monograph_kc_strength,
            "candidate_domains": candidate_domains,
            "candidate_domain_kccs": candidate_domain_kccs,
            "candidate_domain_assays": candidate_domain_assays,
            "candidate_domain_references": candidate_domain_references,
            "candidate_domain_validation_examples": candidate_domain_validation_examples,
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
            "notes": {
                "evidence.score": (
                    "0-4, comparable only within the same source_track. 10yr-iarc counts 3 "
                    "primary model systems; vol100-kc counts 4 information sources."
                ),
                "evidence.direction": (
                    "positive / protective / equivocal / negative / unspecified. A protective cell always has score 0."
                ),
                "evidence.source_count": (
                    "Raw count the score derives from, where the source supplies one. "
                    "Denominator differs by track; null for label-derived scores."
                ),
            },
            # Row counts and checksums: a consumer cannot otherwise tell a
            # truncated or corrupted download from a complete one, and the UI
            # calls the JSON a "full normalized dataset".
            "tables": {
                name: {
                    "rows": int(len(df)),
                    "columns": [str(c) for c in df.columns],
                    "csv_sha256": _sha256(out / f"{name}.csv"),
                }
                for name, df in tables.items()
            },
            "total_rows": int(sum(len(df) for df in tables.values())),
            "checksums": {
                fname: _sha256(out / fname)
                for fname in (csv_bundle, json_file, parquet_bundle)
            },
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
    parser.add_argument("--tag", default=APP_VERSION, help="Release tag (defaults to the version in pyproject.toml)")
    args = parser.parse_args()
    path = export_release(args.tag)
    print(f"Exported to {path}")


if __name__ == "__main__":
    main()
