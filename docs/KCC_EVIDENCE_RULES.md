# KCC Evidence Scoring Rules

This document defines the deterministic algorithm used to derive
`evidence.score` (0–4) values from peer-reviewed source tables. The intent is
that any future curator (human or automated) can reproduce the score in any
direction — and that disagreements stay traceable to a specific cell in a
specific source publication.

## Score scale

| Score | Label        | Meaning                                             |
| :---: | :----------- | :-------------------------------------------------- |
|   0   | No evidence  | All available signals are negative or absent        |
|   1   | Equivocal    | Mixed / inconclusive evidence, no convergent “yes”  |
|   2   | Moderate     | Single-model-system positive evidence               |
|   3   | Strong       | Two-model-system convergent positive evidence       |
|   4   | Convincing   | Three-model-system convergent positive evidence     |

The scale is intentionally cumulative: a higher score implies the data
required for every lower score is also present.

## Source 1 — IARC 10-year retrospective (Rusyn et al. 2024)

**Reference id:** `rusyn2024-tenyears` (DOI [`10.1093/toxsci/kfad134`](https://doi.org/10.1093/toxsci/kfad134))
**Tables produced:** `iarc_monograph_kc_calls`, `iarc_monograph_kc_strength`
**Evidence rows produced:** `source='10yr-iarc'`, `curator_notes` starts with `[10yr-iarc]`

### Cell vocabulary (File012 — Supplementary File 12)

Each of the 19 IARC Monograph volume sheets (Vol 112–130) gives one cell per
(agent × model-system × KC). Values verbatim from the paper:

| Verbatim                                       | Canonical `call` | Score contribution                         |
| :--------------------------------------------- | :--------------- | :----------------------------------------- |
| `Yes`                                          | `Yes`            | Counts toward positive convergence         |
| `No`                                           | `No`             | Negative — counts toward score 0           |
| `Equivocal`                                    | `Equivocal`      | Floors the score at 1 if no `Yes` present  |
| `Protective`, `Antioxidant`, `Antiinflammatory`| `Protective`     | Treated as negative; raw label preserved   |
| (blank)                                        | (no row)         | Does not contribute either way             |

`Protective` is **not** positive evidence: the agent is reported to actively
*suppress* the KC (e.g. drinking coffee → KC5 oxidative stress = Protective in
Vol 116). The paper-verbatim label is preserved in `iarc_monograph_kc_calls.raw_call`
so curators can split downstream surfaces (e.g. a `protective_for` filter).

### Aggregation rule

For each (agent, KC) pair the importer counts calls across the three model
systems (`Exposed Humans`, `Human cells in vitro`, `Mammalian in vivo`) and
across however many volumes covered the agent. The rule:

```
if   yes_count >= 3:   score = 4   # convergent across all 3 model systems
elif yes_count == 2:   score = 3   # convergent across 2 model systems
elif yes_count == 1:   score = 2   # single-system positive
elif equivocal >= 1:   score = 1   # equivocal floor
else:                  score = 0   # all-negative (No / Protective)
```

A `curator_notes` field is filled with the call breakdown
(`Yes×2, Equivocal×1, ...`) and the contributing volume numbers, so any later
review can audit the score without re-opening the source XLSX.

### Strength labels (File014 — Supplementary File 14)

`iarc_monograph_kc_strength` carries the paper-standardized
**Strong / Moderate / Weak** label per (agent, KC), plus the IARC
**Mechanistic data role** (`Supportive`, `Upgrade`, `Not used`) describing how
the row fed into the final cancer-hazard evaluation. These labels are stored
*verbatim* and **do not feed `evidence.score`** — they live alongside as an
independent qualitative axis, surfaced as chips on the agent and KCC detail
pages.

## Source 2 — KCAD (Rigutto et al. 2025)

**Reference id:** `kcad-paper-rigutto-2025` (DOI [`10.1093/database/baaf026`](https://doi.org/10.1093/database/baaf026))
**Tables produced:** `assay_annotations`, `assay_kc_subgroups`, `assay_study_designs`, `kcad_abbreviations`, `kcad_column_definitions`
**Evidence rows produced:** none (KCAD is an assay-centric catalog; curator scoring is left untouched).

KCAD provides per-assay annotations but no agent-level evidence scores. The
importer only attaches `EvidenceCitation` links to existing curator-scored
rows where a (agent, KCC, reference) triple coincides; it never creates or
mutates `evidence` rows.

## Provenance & override order

When multiple sources cover the same (agent, KC) pair, the importer respects
the following precedence (highest authority first):

1. **Curator-scored rows** — any `evidence` row whose `curator_notes` does
   not start with `[10yr-iarc]` is considered curator-authored and is never
   overwritten by an automated importer.
2. **Peer-reviewed 10-yr retrospective** — `source='10yr-iarc'` rows.
3. **(future)** Other peer-reviewed evidence sources, added with their own
   `[source-tag]` prefix in `curator_notes`.

A curator who disagrees with an aggregated 10-yr score simply edits the row;
re-running the importer will *not* clobber the edit (the reset step only
deletes rows whose `curator_notes` start with `[10yr-iarc]`).

## How to extend

To add a new peer-reviewed source X:

1. Seed its `Reference` row in `db/seed/refs/foundational.json`.
2. Write a parser that returns canonical calls (Yes/No/Equivocal/Protective)
   per (agent, KC, sub-context).
3. Use the same aggregation rule above (or document an alternative explicitly
   in this file).
4. Prefix every produced `curator_notes` with the source tag, e.g.
   `[<source-tag>] <free text>`. The reset step in the importer keys on this
   prefix.
