# Known limitations and planned changes

This file records limitations that are **known and deliberate**, not overlooked.
Each entry states what is wrong, why it was not fixed in the current release, and
what fixing it requires. Where a limitation affects how a number should be read,
the application says so at the point of use — this document is the index, not the
disclosure.

Current release: **0.0.10 → 0.0.11**. Items below are targeted at **0.1.0**,
which is the first release permitted to change scores, agent ids or the API
contract.

---

## 1. The 0–4 scale carries three different measurements

**What is wrong.** The same `Limited / Substantial / Convincing` vocabulary is
applied to three unlike quantities:

| Derivation | Cells | What the number counts |
|------------|------:|------------------------|
| Standardized strength label (Rusyn et al. 2024, File 14) | 250 | A published expert judgement, mapped one rung up |
| Positive calls in 3 primary model systems (File 12) | 252 | Author-coded convergence across model systems |
| Shaded information-source types (Krewski et al. 2019, Fig. 22.4) | 342 | How many of four source types reported anything |

The methodology page states that the Volume 100 numbers are "a count of source
types — not a strength judgement", which is precisely the point: they should not
share a vocabulary with the other two.

**Why it is not comparable even within one source.** 62 of the 73 ten-year
agents carry both label-derived and count-derived cells, so filtering to one
source does not make a profile internally consistent.

**IARC's own methodology** weighs study quality, validity, informativeness,
consistency and coherence — not the number of systems in which a signal appears.
A count-derived 3 is not the same kind of claim as a Working Group label.

**Planned fix (0.1.0).** Promote the derivation to a first-class field
(`derivation_method` ∈ `wg_strength_label`, `author_call_coverage`,
`vol100_source_coverage`), display the raw label or count with its denominator
instead of a shared tier name, and stop ranking the three together unless the
combined scale is independently validated.

**Interim disclosure (0.0.11).** Every cell carries `source_track`,
`source_count`, `data_role`, `direction` and a derivation note; the Methodology
page states the three derivations and their denominators separately; the doc and
the app both say that filtering by source is insufficient.

---

## 2. Strength, direction and IARC data role are not independent dimensions

**What is wrong.** `kcc_coverage()` and `count_at_least()` key on `score` alone.
Consequently:

* 53 cells scoring ≥2 have a non-positive primary direction (11 `negative`,
  13 `equivocal`, 29 `unspecified`) and still count as coverage.
* 145 cells scoring 2–4 are marked `Not used` by the IARC Working Group and
  still count toward every ranking.

Example: 3-chloro-2-methylpropene × genotoxicity scores **4** with
`direction = equivocal` and `data_role = Not used`.

**Planned fix (0.1.0).** Treat source strength, observed direction and IARC data
role as three independent dimensions. Compute "positive coverage" only from
explicitly positive cells, and expose the others as separate counts rather than
folding them into one number.

**Why not now.** It changes every published coverage and ranking figure,
including in release bundles already downloaded. It needs a version boundary.

**Interim disclosure (0.0.11).** Matrix, fingerprint and radar mark every
non-positive direction with its own glyph and tooltip; `Not used` cells carry a
`□`; the CSV export carries `direction` and `iarc_data_role` per cell; the
Methodology page quantifies both residuals.

---

## 3. Combined evaluation units are modelled as single agents

**What is wrong.** Two agents merge exposures IARC classified separately:

| hKCC agent | Group held | What IARC concluded |
|------------|-----------|---------------------|
| `red-and-processed-meat` | 2A | Processed meat **Group 1**; red meat **Group 2A** |
| `drinking-mate-and-very-hot-beverages` | 2A | Very hot beverages **Group 2A**; maté not drunk very hot **Group 3** |

**Planned fix (0.1.0).** Either split them into separate agents, or model
classification as a qualified record — exposure definition, group, volume, year,
source — so one substance can hold several evaluations without collapsing them.

**Why not now.** Splitting changes agent ids, which breaks saved queries,
citations and any downstream join. It needs a deprecation path.

**Interim disclosure (0.0.11).** Both agent pages carry a "Combined exposure"
warning naming the component classifications.

---

## 4. Two IARC groups exist for three agents

`agents.iarc_group` disagrees with the group recorded in the source strength
table for **aldrin** (3 vs 2A), **dieldrin** (3 vs 2A) and **ortho-nitroanisole**
(2B vs 2A; IARC reports 2A in Volume 127).

**Planned fix (0.1.0).** Adjudicate against the monographs and model the
classification as a sourced record with volume and year, so a disagreement is
representable rather than a silent overwrite.

**Interim disclosure (0.0.11).** `iarc_group_conflicts()` detects the
disagreement from the data and Agent Detail shows both values, stating that hKCC
does not adjudicate between them.

---

## 5. Candidate domains cannot yet be evaluated against their own evidence bars

**What is wrong.** Each domain declares a minimum evidence bar ("a functional
coupling assay at non-cytotoxic concentrations") and explicit exclusions. None of
it is enforceable: `assay_annotations` stores no dose, duration, route,
comparator, effect size, cytotoxicity, replication or study-quality field, so
there is nothing to test a bar against.

Related gaps:

* EMD1 has no assay or reference mappings at all.
* The EMD1–4 source (`kazi2026-emd`) is recorded as a 2026 "Manuscript" with no
  DOI, PMID or URL.

**Planned fix (0.1.0).** Add observation-level exposure and quality fields, which
requires a curation source beyond KCAD — KCAD does not carry them.

**Interim disclosure (0.0.11).** The Layer 2 section is labelled **provisional**
and states that the bars cannot be enforced; assay links now expose their
`evidence_level` through the API so a consumer can apply a domain's own exclusion
rule; the CD5 connexin assay was reclassified `descriptive` after it was found
tagged `functional` in contradiction of CD5's own exclusion; domains with no
mapped assays are flagged in the UI.

---

## 6. `agent_sites` is empty

The schema models tumour sites; the shipped database has 0 rows. The UI hides the
column and metric when empty, and `docs/DATABASE_TABLES.md` records the row count
as 0. Populating it from monograph tumour-site listings is a curation task, not a
code change.

---

## 7. Reference identity is not canonical

**What is wrong.** `references` holds one row per source-specific citation, not
per published work:

* **60 DOIs appear on more than one row.** Nothing merges them into a single
  work identity.
* **106 rows have a placeholder title** (`—`). They participate in **11,638**
  annotation links and **77** evidence-citation links, so a reader following a
  citation can land on a record with no title.
* Citations carry no role. A derivation source, a supporting study and a
  background paper are stored and displayed identically.

**Planned fix (0.1.0).** Canonical work identities keyed on normalized DOI/PMID,
with source-specific rows becoming aliases; a `citation_role` distinguishing
derivation / support / background; a curation pass over the placeholder titles.

**Fixed in 0.0.11 (partial).** Literature de-duplication now keys on DOI, then
PMID, then `(year, title)`, and **refuses to merge rows whose identifiers
disagree** — it previously merged two distinct 1981 hexachlorocyclohexane papers
into one card. Placeholder-titled rows are excluded from the Literature list.

---

## 8. Ordinal scores are drawn as proportional magnitudes

Bar height, progress fill and radar sector radius are all proportional to the
score, which implies a ratio scale the derivations do not support — a 4 is drawn
twice as far as a 2 while meaning "3 of 3 systems" against "1 of 3".

**Planned fix (0.1.0).** A discrete encoding (stepped ticks or categorical
bands) that cannot be read as a magnitude. Deferred because it changes every
figure in the product and pairs naturally with item 1.

**Interim disclosure.** The ordinal warning appears on the Methodology page and
the label-offset note on every page that shows a score.

---

## Fixed in 0.0.11

* Score-zero documentation claimed 144 cells were supplementary-positive; only 32
  are. The other 112 hold no positive call in any system. Documentation corrected
  and the test strengthened — it previously checked only that *some* call existed.
* Per-model-system calls were described as extracted verbatim from IARC
  Monographs. They are Rusyn & Wright's retrospective author coding; only the
  strength label and data role are Working Group outputs.
* CD5's connexin assay was tagged `functional` against CD5's own exclusion.
* `evidence_level` was discarded by the domains API.
* Documentation asserted that per-agent counts are internally consistent because
  no agent mixes tracks; 62 of 73 mix derivations *within* a track.
* `GET /assays/{id}/annotations` capped at 500 rows with no cursor, silently
  truncating five assays — the largest returned 500 of 7,874. Now paginated with
  `total`, `count` and `next_cursor`, plus agent/KCC/design filters.
* The shipped SQLite file carried 2 of the 5 constraints `evidence` declares.
  `hkcc/db/schema_repair.py` rebuilds such a table from the ORM's own DDL, and
  runs on start-up so existing copies heal themselves.
* `/health` reported "ok" without touching the database; it now returns 503 when
  the database is unreachable.
* `kcc_stats()` had no API branch and opened the bundled SQLite file even when
  API-backed.
* Two search widgets bound to `?q=` on the same page caused an endless rerun
  loop on Browse KCCs, Carcinogens and Assays.
* A missing citation count rendered as "0 cites"; it now reads "cites n/a".
* A test of documented API paths ended in `or True` and could never fail.
* Release manifests now carry per-table row counts, column lists and SHA-256
  checksums, plus a checksum per downloadable bundle.
* The Carcinogens CSV export dropped `direction` and `source_track`.
* Clickable table rows were mouse-only: they now have `role`, `tabindex`,
  `aria-label` and Enter/Space handling.
* Dark-mode accent measured 3.58–4.17:1 against the three grounds and light-mode
  muted 3.98:1 — both below the 4.5:1 WCAG AA threshold for body text. Retuned;
  a test now fails if any token/ground pair drops below AA.
