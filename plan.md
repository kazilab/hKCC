# hKCC v0.5 — Close the design gap

Implementation plan to bring the production Streamlit app (`app/`, `api/`, `db/`)
into closer alignment with the JSX/HTML mockup (`hKCC.html`, `screens/*.jsx`,
`components.jsx`, `data.js`, `styles.css`).

The mockup is **design reference only** — do not port JSX wholesale. Re-create
the same information architecture, visual hierarchy, and interactions inside
Streamlit, using `components.html` for anything Streamlit's stock widgets can't
express.

Backend (DB schema, API, seed, pipelines, tests) is already ~95% complete —
nothing in this plan touches it unless explicitly noted.

---

## Conventions

- All work targets the existing `app/` Streamlit codebase.
- Reuse `app/theme.py` (`HKCC_CSS`, `THEME`, `EV_COLORS`) — extend, don't fork.
- Custom HTML chunks belong in `app/components/` (one module per component) and
  render via `streamlit.components.v1.html` with explicit `height`.
- Preserve existing tests; add new tests under `tests/` for any new helper.
- Reference files in `screens/*.jsx` for the *visual* target; reference
  `data.js` only as a fallback when seed data is missing — production reads
  from Postgres via `app/data_client.py`.

---

## P0 — Visual identity & shell (biggest perception gap)

### P0-1. Add the "paper" (light, warm) theme as the default
Mockup default is `data-theme="paper"`. Only `dark` shipped.

- Add a `PAPER` palette to `app/theme.py` mirroring the mockup CSS variables
  in `styles.css`:
  - `paper #F7F4ED`, `paper-2 #FFFFFF`, `paper-3 #EFE9DC`
  - `ink #1F1B14`, `ink-2 #3A342A`, `muted #807868`
  - `rule #E2DBC9`, `accent #8B2E2A`, `teal #2D5959`
  - Evidence ramp: `#EFE9DC, #E6C9A8, #D69A6B, #B36344, #8B2E2A`
- Refactor `theme.py` so `HKCC_CSS` and `EV_COLORS` are produced from a
  `_palette(name)` factory; expose `get_theme(name)` returning `(THEME_DICT, CSS, EV)`.
- Default theme = `paper`. Read override from
  `st.session_state["hkcc_theme"]` or `?theme=dark` query param.
- Every page already calls `st.markdown(f"<style>{HKCC_CSS}</style>", ...)` —
  swap that for a `apply_theme()` helper in `app/theme.py` so theme switching
  happens in one place.

**Acceptance**: setting `?theme=paper` (or default) renders cream backgrounds,
brick accent; `?theme=dark` keeps current behaviour.

---

### P0-2. Custom sidebar (sectioned nav + counts + brand block)
Replace the stock `st.navigation` chrome with a custom sidebar matching
`components.jsx → Sidebar`.

- New module `app/components/sidebar.py`. Render via `st.sidebar` + raw HTML.
- Sections + items (use `pages/*.py` paths via `st.switch_page`):
  - **Browse**: Overview, The 14 KCCs (`14`), Carcinogens (count from DB)
  - **Analyze**: Evidence matrix, Assays & methods (count), Literature (count)
  - **Build**: Data & API, About hKCC
- Brand block: `h<accent>KCC</accent>` in Instrument Serif + subtitle.
- Active state from `st.session_state["__page"]` (set on each page top).
- Footer: `v{release_tag} · build {build_no}` + "Last sync · {date}".

Keep `st.navigation` registered for keyboard/URL fallback but hide its visual
sidebar with CSS (`[data-testid="stSidebarNav"] { display: none; }`).

**Acceptance**: sidebar matches mockup layout (Browse / Analyze / Build labels,
counts on the right, brand at top, version footer).

---

### P0-3. Topbar with breadcrumbs + global search
Mockup has a persistent topbar (`components.jsx → Topbar`). Streamlit doesn't,
but a per-page HTML block is cheap.

- New `app/components/topbar.py: render_topbar(page_key)`.
- Each page calls it as its first content line. Breadcrumb map matches
  `components.jsx`'s `crumbsFor`.
- Search input is non-functional for v0.5 — wire it to a `st.query_params`
  update that, on Overview/Carcinogens/KCCs/Assays, pre-fills the page's
  existing search box. Show `⌘K` kbd hint; behaviour can be a real palette
  later.

**Acceptance**: every page shows the same topbar; breadcrumbs reflect the
mockup; search hint visible.

---

## P1 — High-value content gaps

### P1-1. Overview page — restore the three missing sections
Current `app/pages/1_Overview.py` ships only the headline, stats, and KCC grid.
Add, in order, matching `screens/home.jsx`:

1. **Featured agents** ("Most-queried agents this week"): hardcoded ID list
   `["tobacco-smoke", "benzene", "asbestos", "tcdd", "ethanol", "arsenic"]`
   — render each as a clickable card row with serif name, group chip, CAS+type
   line, coverage `N/14`, and a 14-cell inline KCC fingerprint strip.
   - Click → `st.switch_page("app/pages/4_Agent_Detail.py")` with
     `st.query_params["agent_id"] = id`.

2. **Recent literature**: top 5 from `list_references()`, year+tag eyebrow,
   serif title, mono author/journal/vol line. Click → Literature page.

3. **Evidence ramp explainer card**: two-column block with
   - Left: "How to read this" eyebrow + serif sub + two prose paragraphs
     (copy from `home.jsx`)
   - Right: evidence legend strip + an EXAMPLE row showing Benzene's 14-cell
     fingerprint and weighted score (`{total}/56`).

Implement the fingerprint strip in `app/utils/evidence.py:fingerprint_html(scores, kccs)`
returning a small HTML chunk — reuse from Carcinogens table (P1-2).

**Acceptance**: Overview scrolls through hero → stats → KCC grid → featured
agents → recent literature → explainer card → footer.

---

### P1-2. Carcinogens table — inline KCC fingerprint column
Mockup table has a 14-swatch column per row. `st.dataframe` can't render HTML
cells, so:

- Replace the `st.dataframe` call in `app/pages/3_Carcinogens.py` with a single
  `components.html` table built in `app/components/agent_table.py`.
- Columns: Agent (serif) · CAS (mono) · Type · IARC chip · Tumour sites ·
  KCC fingerprint (14 cells) · Coverage `N/14`.
- Rows are clickable (target a hidden `<a href="?agent_id=...">` that sets the
  query param; on rerun the page detects it and switches to Agent Detail).
- Preserve existing filters/sort and CSV/JSON exports.

**Acceptance**: the table shows fingerprints inline; clicking a row opens the
agent profile.

---

### P1-3. Data & API page — full explorer rebuild
`app/pages/8_API_Downloads.py` is a thin selectbox. Rebuild to match
`screens/api.jsx`:

1. **Top: three download cards** (CSV / JSON / Parquet) showing size + filename
   for the current release tag. Size pulled from `pipelines.export_release` if
   the export exists; otherwise show `—`. Buttons trigger `st.download_button`
   pointing at the on-disk export.

2. **Two-column API explorer**:
   - Left: vertical list of endpoint buttons with `GET`/`POST` method chip and
     path. Selected button highlighted (ink background).
   - Right: sample response in a dark `<pre>` block. Sample bodies live in a
     new `app/data/api_samples.py` module (the JSON shown in `screens/api.jsx`).
     Replace `kcc-02` etc with values from the live DB where cheap.
   - Below: "Try live request" button (existing logic) + "Copy" button.

3. **Auth tiers**: three cards — `PUBLIC / RESEARCHER / CURATOR` — copy
   verbatim from `screens/api.jsx`. Static for now; ORCID auth is v2.

4. **Quickstart snippets**: Python + R code blocks (copy from `screens/api.jsx`),
   each in a card with "Copy ↗" button.

5. Keep the **Live feeds** tab as a second top-level tab — it's the only
   addition beyond the mockup and works.

**Acceptance**: page resembles `screens/api.jsx` end-to-end; existing live
request and export functionality preserved.

---

### P1-4. Evidence matrix — add `bar` style
Mockup matrix has 4 styles. `app/components/matrix.py` implements 3.

- Add `bar` branch to `matrix_heatmap_html`: when `matrix_style == "bar"` and
  `v > 0`, render an inner `<span>` of height `${(v/4)*100}%` anchored to the
  cell bottom, coloured `var(--accent)`, leaving the cell background neutral.
- Add `bar` to the selectbox in `5_Evidence_Matrix.py`.

**Acceptance**: switching to "bar" shows vertical fills inside otherwise empty
cells.

---

## P2 — Polish & secondary improvements

### P2-1. KCC detail screen
`screens/kccs.jsx` has a dedicated `ScreenKCCDetail` (per-KCC page) with
linked carcinogens, key assays, anchor references. Production collapses this
into an in-page selectbox panel.

- Add `app/pages/2a_KCC_Detail.py` keyed by `?kcc_id=...`.
- Header: KCC number, glyph, title, "Original 10" / "Extended" chip.
- Description + mechanism prose.
- Three sections:
  - **Linked carcinogens** (agents with evidence ≥ 2 on this KCC), sortable
    by score, click → agent detail.
  - **Key assays** (`Assay.kcc_links` join), grid of cards.
  - **Anchor references** (`ReferenceKCC` join), list.
- Wire from KCC grid cards on Overview & Browse pages — switch_page to here
  instead of inline panel.

**Acceptance**: clicking any KCC anywhere opens a dedicated detail page.

---

### P2-2. Literature page styling
Match mockup card style: serif italic title, year accent eyebrow, tag chip.
- Replace `st.container(border=True)` with a `components.html` card per ref
  inside `app/components/ref_card.py`.
- Keep the year-histogram + tag-filter logic.

---

### P2-3. Tweaks panel parity (optional)
Mockup `app.jsx` exposes Theme / Accent / Density / Serif headings / Matrix
style under a Tweaks panel. In Streamlit, expose the same set as a single
expander pinned in the sidebar:
- Theme: paper / dark (radio)
- Accent: 4-swatch picker (colour set from mockup)
- Density: comfortable / compact (radio) — toggles a `data-density` attribute
  on body, with CSS rules in `theme.py` adjusting paddings
- Serif headings: toggle (swaps `--font-serif` for `Public Sans`)
- Matrix style: heatmap / dot / bar / number

Persist to `st.session_state` and apply on every rerun via `apply_theme()`.

---

### P2-4. Per-cell citations in Detailed-evidence tab
`Evidence.n_refs` and `EvidenceCitation` are seeded but `4_Agent_Detail.py`
hardcodes the "Anchored to N references" line.

- In `app/data_client.py`, expose `evidence_for_agent(agent_id) → list[{kcc_id, score, n_refs, refs: [...]}]`.
- In the Detailed evidence tab, render the actual ref count and (collapsed
  by default) the linked references per KCC row.

---

## Out of scope for v0.5

- ORCID curator UI / write-side workflow (`Revision` table is ready — UI v2).
- Real `⌘K` command palette (the topbar input is a stub for now).
- PNG snapshot export of the matrix.
- Mobile/responsive optimisation — desktop-first remains target.

---

## Suggested execution order

1. P0-1 (paper theme) → unblocks visual review of everything else.
2. P0-2 (sidebar) + P0-3 (topbar) together — shared shell.
3. P1-1 (Overview sections) — quickest user-visible win.
4. P1-2 (Carcinogens fingerprint column) — biggest table fix.
5. P1-3 (API page rebuild) — largest single page rewrite.
6. P1-4 (matrix bar style) — trivial.
7. P2 items in any order, time permitting.

Each P0/P1 item should ship as its own PR with a screenshot diff against the
matching `screens/*.jsx` artifact.
