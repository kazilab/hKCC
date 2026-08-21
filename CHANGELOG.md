# Changelog

All notable changes to hKCC. Dataset and code are versioned together; the
version lives in `pyproject.toml` and nothing else hardcodes it.

## [Unreleased]

### Changed
- **`candidate_domain_kccs.relation` now takes four values** — `home`,
  `downstream`, `upstream`, `contrastive` — replacing `primary`/`secondary`.
  The old pair was carrying four meanings at once (*files here*, *causes this*,
  *is caused by this*, *is the opposite of this*), which left two links pointing
  the wrong way down the causal chain and one link unstatable. Section 3 of the
  manuscript requires explicit attribution of direction; the schema can now
  express it. Migrate with
  `python -m hkcc.pipelines.migrate_domain_relations --apply`.
- Reassigned all 19 EMD–KCC links from the link-by-link audit against §4, §5.1–5.4,
  the KCC scope text, and the shipped assay annotations. Six links are now `home`
  where sixteen were `primary`, so the designation discriminates again.
- **EMD4–KCC9 is `contrastive`, not a home.** KCC9 is defined as *bypass* of
  replicative senescence; EMD4 measures *induction* of it. As a primary home it
  filed an agent under a characteristic meaning the opposite of what was observed.
  The link is kept — it is evidentially adjacent — but can no longer read as a
  positive.
- **EMD1–KCC5, EMD3–KCC8 and EMD4–KCC5 are `upstream`.** In each, the KCC induces
  the domain rather than following from it (§5.1 "redox stress *mediates* the
  change"; §5.3 "receptor signalling *controls* the transition").
- `2_Browse_KCCs` shows the four relations separately, and marks the contrastive
  link as never a positive.

### Added
- `EMD2–KCC2` (`downstream`). The platform already shipped a
  *"Colibactin / genotoxin adduct & pks-island detection"* assay under EMD2 while
  the mapping table denied any KCC2 link; a bacterially produced genotoxin forming
  DNA adducts is KCC2.
- API fields `home_kcc_ids`, `downstream_kcc_ids`, `upstream_kcc_ids`,
  `contrastive_kcc_ids` on `/api/v1/domains`. `primary_kcc_ids` /
  `secondary_kcc_ids` are kept for compatibility and collapse to `home` and
  not-`home`, discarding direction.
- `hkcc.pipelines.migrate_domain_relations`, a documented dry-run/`--apply`
  migration carrying the audited mapping and its per-link rationale.
- Tests: every domain must have at least one `home`, and `contrastive` is pinned
  to the single EMD4–KCC9 link so it cannot spread without a manuscript change.

### Note
- `CD5` (gap-junctional communication) is outside the manuscript's four domains and
  was **not** audited. Its links were carried over structurally (`primary`→`home`,
  `secondary`→`downstream`) and need separate review.

## [0.0.10]

Consolidates the pre-publication review: two data sources, a package that ships
its own dataset, and documentation that the test suite keeps honest.


### Added
- **IARC Volume 100 Group 1 re-review** (84 agents) from Krewski et al. 2019,
  Sci. Pub. 165 Ch. 22, Fig. 22.4. Brings asbestos, arsenic, tobacco smoking,
  formaldehyde, aflatoxins, crystalline silica and the rest of the classic Group 1
  set into the database. Group 1 agents: 7 -> 91.
- Second evidence track, tagged `[vol100-kc]`, with its own documented derivation
  (colour intensity = number of information sources) and its own tests.
- `hkcc` console entry point (`hkcc`, `hkcc api`, `hkcc info`) and a PyPI-installable
  package carrying the dataset inside it.
- Controlled `agent_type` vocabulary, enforced by tests.
- CI: lint and tests on Python 3.11-3.13, plus a packaging job that proves the
  wheel ships the dataset and serves it from any directory.
- Landing page at `docs/index.html`.

### Changed
- Restructured into a single `hkcc/` package; the dataset moved to
  `hkcc/data/hkcc.db` and ships with the distribution.
- **Never-assessed (agent, KC) pairs no longer render as 0.** The matrix, the API
  and the CSV exports omit them; the UI marks them "not assessed". Previously
  ~716 pairs asserted negative evidence that no source had reported.
- `docs/KCC_EVIDENCE_RULES.md` rewritten to describe how scores were actually
  derived, and made verifiable: tests recompute every score from the source tables.
- Merged four duplicate agent records; resolved TCAB's conflicting IARC group.
- Reclassified agents that were filed as "Industrial chemical" by an import
  default (night shift work, welding, coffee, processed meat, opium, and three
  pesticides).
- Normalised agent names: ALL-CAPS source labels, Greek letters, and two source
  typos corrected (Molybdenum trioxide, isobutyl nitrite).
- Dataset exports now include the cell-level citation links.

### Fixed
- Rate limiting on `POST /contribute` could be bypassed by rotating
  `X-Forwarded-For`; proxy headers are now trusted only when configured.
- The landing page featured six agent ids that no longer existed, rendering an
  empty section and showing benzene with zero evidence.
- Two pages (Methodology, IARC matrix) were unreachable from navigation.
- Malformed RIS citation export; missing author and URL fields.
- `pdf_path` leaked server paths through the public API and was bound to the
  wrong references; removed.

### Removed
- One-off import pipelines that depended on source files never distributed with
  the repository, and the container/Postgres scaffolding that was never built.
- A 1.2 MB minified bundle in `docs/` that carried its own stale copy of the data.

---

### Bumping the version

`pyproject.toml` is the source of truth — `hkcc/db/config.py` reads it, so the
app, API, `/health` and citation exports all follow automatically. Three files
carry a copy that must be updated by hand:

- `CITATION.cff`
- `docs/index.html` (footer)
- `docs/DATABASE_TABLES.md` (example release tag)
