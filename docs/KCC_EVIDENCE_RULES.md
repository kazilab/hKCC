# KCC Evidence Scoring Rules

This document defines how every `evidence.score` (0–4) in `hkcc.db` was derived
from peer-reviewed source tables. It describes the shipped data exactly:
`tests/test_evidence_rules.py` recomputes the 502 rows of the 10-year track
from the `iarc_monograph_*` tables and asserts they match, and checks the
Volume 100 track against its own rules — so this document cannot drift from the
database without the test suite failing.

There are **two sources**, distinguished by the prefix on `evidence.curator_notes`:

| Prefix | Source | Rows | Coverage |
|--------|--------|-----:|----------|
| `[10yr-iarc]` | Rusyn et al. 2024 | 502 | IARC Monograph Volumes 112–130 |
| `[vol100-kc]` | Krewski et al. 2019, IARC Sci. Pub. 165 Ch. 22 | 342 | Volume 100 series (Group 1 re-review) |

**The two count different things, and the scale does not reconcile them.**

**Filtering to one source is not sufficient either.** Within the 10-year track,
**62 of 73 agents** carry both label-derived (Track A) and count-derived
(Track B) cells, so a single agent's profile already spans two different
measurements. "Compare within a track" reduces the problem; it does not remove
it. The only safe unit of comparison is a cell read together with its
derivation.

| | 10yr-iarc | vol100-kc |
|---|---|---|
| Counts | primary **model systems** | **information sources** |
| Denominator | 3 (Exposed Humans, Human cells in vitro, Mammalian in vivo) | 4 (human/animal × in vivo/in vitro) |
| Score 2 | 1 of 3 | 1 of 4 |
| Score 3 | 2 of 3 | 2 of 4 |
| Score 4 | 3 of 3 | **3 or 4 of 4** |
| Uses score 0 / 1 | yes | never — the source has no negative or equivocal category |

A score of 3 therefore means "two of three model systems" on one track and "two of four
sources" on the other. **Scores are comparable within a track, not across tracks.**

Every evidence row records which track produced it in `evidence.source_track`, and the raw
count in `evidence.source_count` where the source supplies one — so the collapse of *3 or 4
sources* into score 4 is no longer lossy (60 cells at 3 sources, 44 at
4). `source_count` is null for the 250
rows scored from a File014 strength label rather than a count.

No agent mixes *tracks* — but that is a weaker guarantee than it looks, because most
agents mix *derivations* inside the 10-year track (above). An agent's coverage and
threshold counts (cells ≥2, ≥3, ≥4) are therefore **not** built from one measurement, and
should be read as "how many characteristics clear this bar under their own derivation",
not as a single quantity. Ranking *across* agents compares scales as well, so the app shows
the source on every featured card and agent page, offers a source filter on the
Carcinogens list, and warns when a cross-source sort is applied. The matrix CSV carries
`source_track`, `direction`, `iarc_data_role` and `source_count` per cell.

## The scale is ordinal — count scores, do not sum them

0–4 is an **ordinal** scale. A 4 ("Convincing") is not twice a 2 ("Limited"), and the
derivation rules give no basis for adding scores across characteristics.

There is a concrete reason beyond the general principle. Both count-derived tracks map
`score = count + 1` (one positive system → 2, two → 3, three → 4). A sum of scores is
therefore `sum(counts) + number of assessed cells`, so it rewards **breadth of assessment**
as much as strength of evidence. In the shipped data:

| Agent | Sum of scores | Cells ≥ 3 | Cells = 4 |
|-------|--------------:|----------:|----------:|
| 2,4-Dichlorophenoxyacetic acid | **14** | 2 | 1 |
| Cyclophosphamide | 13 | **3** | **2** |

The sum ranks 2,4-D higher while cyclophosphamide is stronger at every threshold.

**hKCC therefore ranks and displays by counts, never by a sum:**

* `kcc_coverage()` — characteristics scoring ≥ 2
* `count_at_least(scores, 3)` — of which substantial or better
* `count_at_least(scores, 4)` — of which convincing

Rankings order on those lexicographically: breadth first, then strength. The matrix shows a
`≥3` column instead of a summed weight, its footer counts **agents reaching ≥2** per
characteristic rather than adding a column, and the old `Σ / (agents × KCCs × 4)` total is
gone — that denominator counted every never-assessed pair, so it was 51% padding.

`total_evidence()` still exists for a `> 0` test but is documented as exploratory and is not
used for ranking or display. `tests/test_overview_featured.py` fails if it reappears in the
ranking key.

## A score does not stand alone

`evidence.score` is not self-interpreting. Every row therefore carries the fields needed to
read it, and all of them are returned by `GET /api/v1/agents/{id}` and written to the
release export:

| Field | What it tells you |
|-------|-------------------|
| `direction` | Which way the evidence points. `protective` means the agent *suppresses* the characteristic. |
| `source_track` | Which published derivation produced the score. Scores compare only within a track. |
| `source_count` | The raw count behind the score. The denominator differs by track. |
| `data_role` | How the IARC working group used the data — `Not used`, `Supportive`, `Upgrade`. |
| `curator_notes` | The derivation in words, including the source volume. |

**`data_role` deserves particular attention: 102 cells score 3 or 4 while carrying
`Not used`**, meaning the IARC working group did not rely on that mechanistic data in its
evaluation. A high hKCC score is a statement about the published mechanistic evidence, not
about what IARC concluded from it.

The agent page shows this under every characteristic, including those scoring 0 — a 0 is an
assessment, not the absence of one, and hiding it made negative and protective findings
invisible. Characteristics with no row at all remain marked "not assessed".

## Two layers

hKCC implements the annotation model of Kazi et al., *Four Cross-Cutting Mechanistic
Domains for Evidence Mapping with the Key Characteristics of Carcinogens*:

**Layer 1 — the ten established KCCs** (`kccs`). This is the reference ontology and the
only thing that carries an `evidence.score`. Smith et al. 2016.

**Layer 2 — candidate mechanistic domains** (`candidate_domains`). These qualify *how* an
observation arose — by what mechanistic route, at what evidence level — and each parents
onto one or more KCCs. They are **not** key characteristics and carry **no score**.

| Code | Domain | Home KCC(s) | Other links | Provenance |
|------|--------|-------------|-------------|------------|
| EMD1 | Exposure-linked epitranscriptomic regulation | KC4 | KC2, KC3, KC10 downstream; KC5 upstream | Kazi et al. |
| EMD2 | Microbiome-mediated disposition and host response | KC1, KC6 | KC2, KC7, KC8, KC10 downstream | Kazi et al. |
| EMD3 | Phenotypic plasticity and stem-like state transitions | KC4 | KC9, KC10 downstream; KC8 upstream | Kazi et al. |
| EMD4 | Persistent senescence and a characterised SASP | KC6 | KC7, KC10 downstream; KC5 upstream; **KC9 contrastive** | Kazi et al. |
| CD5 | Disrupted gap-junctional intercellular communication | KC10 | KC4, KC8 downstream | platform-only; not one of the paper's four |

Only `home` means "an observation files here". The column above used to read
"Primary KCCs" and collapsed all four relations into one, which is what let
EMD3–KC9 sit as a primary link while the prose said a stem-like state is not
immortalisation. See `candidate_domain_kccs` in
[DATABASE_TABLES.md](DATABASE_TABLES.md).

**Why this matters for scoring.** A candidate-domain annotation must never be counted as an
additional independent positive: the same experiment would otherwise contribute twice, once
as a KCC and once as a domain. hKCC enforces this structurally rather than by convention —
`evidence` has a foreign key to `kccs` and no route to `candidate_domains` at all, so there
is nowhere for a domain to become a score. `tests/test_candidate_domains.py` asserts it.

Each domain also carries a **minimum evidence bar** and **explicit exclusions** (global m6A
abundance alone does not qualify; a taxonomic shift alone is not mechanistic evidence; marker
expression alone cannot separate induction from selection; growth arrest alone is not
senescence). Those gates are the practical contribution of Layer 2 — the KCC framework has
no equivalent.

CD5 is a platform-level candidate, not part of the four domains described in the manuscript.
It is kept separable by its own `source_ref_id` so the distinction survives in exports.

## Simulation-derived validation examples are not evidence

`candidate_domain_validation_examples` holds model-derived annotation and design
guidance from the EMD simulation paper: what a measurement cannot settle, which
competing explanation has to be excluded, and what would discriminate between
them. Four rules govern how they may be read.

1. **They are guidance, not evidence.** A validation example is not an evidence
   cell. It has no `score`, it is not an agent annotation, and it says nothing
   about any particular agent.
2. **They cannot create or modify a KCC score.** There is no column to hold one
   and no foreign key by which one could propagate. As with the domains
   themselves, this is structural rather than conventional.
3. **They are never an independent positive.** Model output cannot be
   double-counted with the empirical observations used to constrain the model —
   those observations are already scored on Layer 1. Counting the model's
   agreement with them as further evidence counts the same experiments twice.
4. **`evidentiary_status` is a kind, not a rank.** `data-constrained`,
   `design-constrained`, `structural`, `illustrative`, `prior-dominated` and
   `predictive` are not ordered. A `structural` result — an algebraic degeneracy,
   say — can be more decisive than a fitted one; it simply answers a different
   question. Nothing in the API, the UI or an export may sort or grade on it.

What they *are* for: sharpening the minimum-evidence bars above. "Global m6A
abundance alone does not qualify" is a rule; `emd1-val-01` is the worked
demonstration of why, including what the average conceals and what resolution
recovers it.

`tests/test_domain_validation_examples.py` asserts all of this, including that
running the seed migration leaves every `evidence` row byte-identical.

## Direction is a separate axis from strength

`evidence.score` measures **how much** positive evidence there is. It does not say
**which way** the evidence points. `evidence.direction` does:

| `direction` | Meaning | Rows |
|-------------|---------|-----:|
| `positive` | Primary systems report the characteristic | 623 |
| `unspecified` | Scored from a strength label with no primary calls tabulated | 173 |
| `negative` | Primary systems report `No` | 22 |
| `equivocal` | Primary systems inconclusive only | 20 |
| `protective` | The agent is reported to **suppress** the characteristic | 6 |

**A `protective` cell always has score 0**, enforced by a database constraint
(`ck_protective_not_positive`) and by `tests/test_evidence_rules.py`. Direction
overrides the strength label: if the primary systems report suppression and none
reports a `Yes`, there is no positive evidence to record, whatever File014 says.

This corrects a real defect. Drinking coffee × KC5 previously scored **2** — presented as
limited positive evidence of oxidative stress — while *every* primary system reported it as
`Protective` or `Equivocal`. The standardized label was `Weak`, and Track A applied it
without checking the sign. Track B had always scored its protective cells 0, so the two
tracks contradicted each other on identical semantics, and both contradicted the statement
below that `Protective` is not positive evidence.

**Read a score with its direction.** `GET /api/v1/agents/{id}` returns `direction` on every
evidence cell; `GET /api/v1/matrix` returns a `directions` map per row, omitting the
`positive` majority. In the UI a protective cell renders as ↓ in the accent colour rather
than on the positive heat ramp.

**Cells where the label outruns the primary calls remain visible rather than silently
overridden.** Track A applies the File014 strength label even when primary File012
systems report no `Yes` — either because no primary row was tabulated
(`direction = unspecified`) or because primary calls are only `No` / `Equivocal`
(`negative` / `equivocal`). Those labels may legitimately synthesise evidence
File012 does not promote to the score, so the scores stand — but `direction` makes
the disagreement explicit instead of invisible. Live counts of this residual
(cells scoring ≥2 under a non-positive primary direction) are published on the
Methodology page as `label_outruns_primary`.

## Score scale

| Score | Label | Meaning |
| :---: | :---- | :------ |
|   0   | None | No positive evidence in the primary model systems |
|   1   | Equivocal | Mixed / inconclusive, no convergent “yes” |
|   2   | Limited | Weakest positive tier (see per-track derivation) |
|   3   | Substantial | Middle positive tier |
|   4   | Convincing | Strongest positive tier |

**Read the scale as ordinal, not as a fixed evidentiary definition.** Two
different derivations feed it (below), and they do not mean the same thing
cell-for-cell. A score is only interpretable together with the
`evidence.curator_notes` field, which records which track produced it and the
underlying counts or label.

> **Naming note.** These tier names deliberately avoid the words *Strong*,
> *Moderate* and *Weak*, because those are the verbatim vocabulary of the
> Rusyn et al. 2024 strength labels and mean something different here — an hKCC
> score of 3 is derived from a source label of **Moderate**, not *Strong*. See
> “Label offset”, below.

## Source — IARC 10-year retrospective (Rusyn et al. 2024)

**Reference id:** `rusyn2024-tenyears` (DOI [`10.1093/toxsci/kfad134`](https://doi.org/10.1093/toxsci/kfad134))
**Tables:** `iarc_monograph_kc_calls`, `iarc_monograph_kc_strength`
**Evidence rows produced:** all 502. Every `curator_notes` begins with `[10yr-iarc]`.

Scores come from one of two tracks. **Track A takes precedence** whenever the
paper published a standardized strength label for that (agent, KC) pair;
Track B is the fallback.

### Track A — standardized strength labels (Supplementary File 14)

Applies to **250 of 502** rows.

| File014 `strength_label` | `evidence.score` | Rows |
| :----------------------- | :--------------: | ---: |
| `Strong`                 | 4 | 92 |
| `Moderate`               | 3 | 95 |
| `Weak`                   | 2 | 63 |

The `Rows` column counts **labels, not scores**: 2 of the 63 `Weak` rows score 0
rather than 2, because their primary systems report the agent as *Protective*.
Direction overrides the label mapping — see "Direction is a separate axis from
strength", above.

`curator_notes` records the label and the IARC mechanistic data role, e.g.
`[10yr-iarc] Rusyn 2024, IARC Monograph Vol(s) 130: File014 standardized
strength = Moderate; role = Not used.`

Two properties of this track must be stated plainly:

**Track A follows File014 even where File12's volume-level "Overall strength"
is lower.** The two supplementary files disagree for **39 (agent, KC) pairs**:
File12 records an overall strength of `Suggestive` while File014's standardized
label is `Moderate` (36 pairs) or `Strong` (3 pairs). hKCC follows File014,
because that is the standardized cross-volume table the paper published for
exactly this purpose — so those pairs score 3 or 4 rather than the 1-2 a
volume-level reading would suggest. This is a systematic upward shift against
the per-volume labels, not a rounding artefact. The File12 overall strength is
preserved verbatim in `iarc_monograph_kc_calls` (model system
`Overall strength`) and is visible per volume on the IARC Matrix page, so the
disagreement can be inspected cell by cell.

**Mixed primary calls are resolved in favour of the positive.** Where the
primary model systems disagree, a single `Yes` is enough to record positive
evidence; the protective override fires only when there is no `Yes` at all.
One pair currently sits in this state (drinking mate and very hot beverages x
KCC-10: `Yes` in human cells in vitro, `Protective` in mammalian in vivo,
scored 2 with `direction = positive`). 27 pairs have conflicting primary calls
of some kind. `direction` records the dominant reading rather than the mixture,
so the per-system breakdown on Agent Detail is the authoritative view for these
cells.

**Label offset.** The mapping shifts every source label one rung up the hKCC
scale. A cell the paper called *Weak* scores 2; *Moderate* scores 3; *Strong*
scores 4. The scale therefore has no score reserved for “positive but weaker
than the paper's weakest label”. When comparing hKCC scores against the source
publication, compare the labels in `curator_notes`, not the numbers.

**Data role is not reflected in the score.** `iarc_monograph_kc_strength.data_role`
records how the IARC working group actually used the mechanistic data:

| `data_role` | Meaning | Rows |
| :---------- | :------ | ---: |
| `Not used`   | The working group did not use this data in its evaluation | 147 |
| `Supportive` | Used as supporting evidence | 65 |
| `Upgrade`    | Used to upgrade the overall classification | 38 |

**147 of the 250 Track A cells carry `Not used`.** Of those, **145 still score
2–4** because the score reflects the published strength label alone; **2 score 0**
because primary systems report the agent as *Protective* and direction overrides
the label. Anyone treating a high hKCC score as “IARC relied on this” will be
wrong for the Not-used cells. The `data_role` is preserved verbatim and exposed
via `GET /api/v1/monograph/strengths` and on every evidence cell.

### Track B — model-system call counts (Supplementary File 12)

Applies to the remaining **252 of 502** rows, i.e. pairs with no File014 label.

> **Attribution.** These per-(agent × model system × KC) calls are **Rusyn and
> Wright's retrospective coding of the monograph content**, not determinations
> made by the IARC Working Groups. The authors coded the volumes themselves to
> build a comparable cross-volume matrix. Only the File014 *standardized
> strength label* and *data role* (Track A) are extracted Working Group outputs.
> A Track B score therefore rests on author coding, and must not be cited as an
> IARC Working Group finding. The UI states this on the IARC Matrix page.

Each Monograph volume sheet gives one cell per (agent × model system × KC):

| Verbatim in the paper | Canonical `call` | Contribution |
| :-------------------- | :--------------- | :----------- |
| `Yes` | `Yes` | Counts toward positive convergence |
| `No` | `No` | Negative |
| `Equivocal` | `Equivocal` | Floors the score at 1 when no `Yes` is present |
| `Protective`, `Antioxidant`, `Antiinflammatory` | `Protective` | Treated as negative; raw label kept in `raw_call` |
| (blank) | (no row) | Does not contribute |

`Protective` is **not** positive evidence: the agent is reported to actively
*suppress* the KC (e.g. drinking coffee → KC5 oxidative stress = Protective in
Vol 116).

Counting `Yes` across the **three primary model systems only** — `Exposed
Humans`, `Human cells in vitro`, `Mammalian in vivo` — pooled over every volume
that covered the agent:

```
if   yes_primary >= 3:   score = 4    # convergent across all three
elif yes_primary == 2:   score = 3    # convergent across two
elif yes_primary == 1:   score = 2    # single-system positive
elif equivocal_primary >= 1: score = 1
else:                    score = 0
```

**Supplementary model systems do not contribute to the score.** The five other
row types — `Mammalian in vitro`, `Other in vivo`, `Other in vitro`,
`ToxCast data`, `ToxRefDB data` — are preserved in full in
`iarc_monograph_kc_calls` and surfaced in the IARC Matrix page, but are treated
as supporting context rather than primary evidence, mirroring how the IARC
working groups used them.

The consequence is material: **144 of the 502 cells score 0 while holding
positive calls in supplementary systems only.** Their `curator_notes` say so
explicitly, e.g. `[10yr-iarc] Rusyn 2024, IARC Monograph Vol(s) 130:
supplementary: No×1.`

### What a score of 0 does and does not mean

`0` is not a statement that a mechanism was investigated and ruled out. Across
the database it covers **four** distinct situations:

| Situation | Cells | What it means |
| :-------- | ----: | :------------ |
| `negative` | 17 | All primary-system calls were `No` / `Protective` (11 `direction = negative`, 6 `protective`). Genuine negative evidence in the systems that count. |
| `supplementary_positive` | 32 | No primary-system row at all, but a supplementary system reported `Yes`. Positive evidence exists; the rule does not score it. |
| `not_scored_by_rule` | 112 | No primary-system row, and the supplementary calls are only `No` (100) or `Equivocal` (12). Nothing positive was reported anywhere. |
| `not_assessed` | 866 | The pair has **no `evidence` row at all**. |

The first three produce a literal score of 0 and account for all 161 of them.
The fourth covers 866 of the 1,710
possible pairs. Those are *not* returned as zeros: `GET /api/v1/matrix` omits them
from the `scores` object, the CSV exports leave them blank, and the UI marks
them "not assessed".

> **Correction (v0.0.11).** Earlier versions of this document collapsed rows 2
> and 3 into a single line reading "evidence exists but only in supplementary
> model systems (144 cells)". That was wrong for 112 of those 144: they hold no
> positive call in any system. Only 32 are supplementary-positive.
> `tests/test_evidence_rules.py` now asserts the split, having previously only
> checked that *some* call existed rather than a positive one.

### How "not assessed" is drawn

Because a gap is the *majority* case — 866 of 1,710 pairs — every view has to
distinguish it from a 0 rather than treat it as an edge case:

| View | Score 0 | Not assessed |
| :--- | :------ | :----------- |
| Fingerprint strip | Palest swatch on the 0–4 ramp | Dashed empty outline |
| Evidence matrix | Palest cell | `·` on the page background |
| Evidence profile (agent detail) | Short stub sector | Empty sector, dashed spoke |
| `GET /api/v1/matrix` | `"kcc-02": 0` | Key absent from `scores` |
| CSV export | `0` | Empty field |

The agent-detail figure is a polar **sector** chart, not a connected radar
polygon. A polygon has no defensible vertex for a gap: placed at the origin it
asserts a negative the sources never reported, and interpolated between its
neighbours it asserts evidence nobody recorded. Sectors also avoid implying that
the ten characteristics lie on a continuum — they are unordered categories, and
the space between KCC-01 and KCC-02 means nothing.

## Source 2 — IARC Volume 100 Group 1 re-review (Krewski et al. 2019)

**Reference id:** `krewski2019-iarcsp165-ch22` (IARC Scientific Publication 165,
Chapter 22, *Analysis of key characteristics of human carcinogens*).
Companion database paper: `rieswijk2019-firstdb` (Al-Zoughool et al. 2019,
[doi:10.1080/10937404.2019.1642593](https://doi.org/10.1080/10937404.2019.1642593)).
**Evidence rows produced:** 342, each prefixed `[vol100-kc]`.

Figure 22.4 of that chapter is a heat map over the 86 Group 1 agents identified up
to and including Monograph Volume 106, covering the whole Volume 100 series. Its
caption states the semantics: *"the intensity of the colour reflects the number of
sources of information (human in vivo, human in vitro, animal in vivo, and animal
in vitro studies) on each key characteristic"*.

| Colour | Sources | `evidence.score` |
| :----- | :-----: | :--------------: |
| Red | 4 | 4 |
| Orange | 3 | 4 |
| Yellow | 2 | 3 |
| Green | 1 | 2 |
| White | none | *no row* |

**Score 1 is unused by this track.** Figure 22.4 has no equivocal category, so
nothing maps to it.

**White is "No Source", not a negative finding.** Those cells produce **no
evidence row at all**, so they render as *not assessed* rather than as a 0.
Writing them as 0 would assert an absence of the characteristic that the source
never claimed. `tests/test_evidence_rules.py` enforces this.

**Precedence.** Where an agent already carried a `[10yr-iarc]` score for a KC, the
Volume 100 value was not written: the 10-year retrospective is more recent and was
authored under the key-characteristics framework, whereas this track is a
retrospective re-coding of Monographs written before the framework existed.

**KCs 11–14 are absent** from this source, which predates the extended set.

## KCAD (Rigutto et al. 2025) contributes no scores

**Reference id:** `kcad-paper-rigutto-2025` (DOI [`10.1093/database/baaf026`](https://doi.org/10.1093/database/baaf026))
**Tables:** `assay_annotations`, `assay_kc_subgroups`, `assay_study_designs`, `kcad_abbreviations`, `kcad_column_definitions`

KCAD is an assay-centric catalogue with no agent-level evidence scores. It
contributes `EvidenceCitation` links to existing cells where an
(agent, KCC, reference) triple coincides, but never creates or changes an
`evidence` row.

## Provenance and precedence

`evidence.curator_notes` is the provenance marker:

1. **Curator-authored** — any row whose notes carry no recognised source prefix.
   None exist in the current release.
2. **Peer-reviewed 10-yr retrospective** — the 502 `[10yr-iarc]` rows.
3. **IARC Volume 100 re-review** — the 342 `[vol100-kc]` rows, applied only
   where the track above left the cell empty.

A curator who disagrees with a derived score edits the row and rewrites
`curator_notes` without the `[10yr-iarc]` prefix, which marks it as
curator-authored and takes it out of scope for any future automated refresh.

## Verifying this document

```bash
pytest tests/test_evidence_rules.py
```

The test rebuilds every score from `iarc_monograph_kc_calls` and
`iarc_monograph_kc_strength` using the rules above and asserts an exact match
against `evidence.score` for all 502 rows, plus the row counts quoted in each
table here. If a future data update changes how scores are derived, that test
fails until this document is updated to match.
