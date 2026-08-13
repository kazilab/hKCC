"""Overview."""

import streamlit as st
import streamlit.components.v1 as components

from hkcc.app.components.glyphs import render_glyph
from hkcc.app.data_client import (
    agents_with_evidence,
    evidence_track_counts,
    kcc_stats,
    list_agents,
    list_assays_count,
    list_kccs,
    list_literature_references,
    list_references_count,
)
from hkcc.app.page_shell import global_search_query, init_page
from hkcc.app.utils.evidence import (
    count_at_least,
    ev_legend_html,
    fingerprint_html,
    has_evidence,
    kcc_coverage,
)

THEME, _ = init_page("overview")

kccs = list_kccs()
agents = list_agents()
stats = kcc_stats()
group1 = sum(1 for a in agents if a.get("iarc_group") == "1")
search_q = global_search_query().strip().lower()

st.markdown('<span class="mono">Live · hKCC</span>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display">Mechanistic evidence for the '
    f'<em style="font-style:italic;color:{THEME["accent"]}">10 key characteristics</em> '
    "of human carcinogens.</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="lede">hKCC is an open database that organises mechanistic evidence '
    "linking carcinogenic agents to the key characteristics framework proposed by "
    "Smith et al. (2016) and extended in the years since.</p>",
    unsafe_allow_html=True,
)
st.caption(
    "Coverage: the IARC Monograph Volume 100 Group 1 re-review (Krewski et al. 2019) and "
    "Volumes 112–130 (Rusyn et al. 2024). **Volumes 107–111 are covered by neither source**, "
    "so agents evaluated only there carry no scores. Scores from the two sources are derived "
    "by different documented rules — see the methodology page."
)

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Browse the KCCs →", type="primary"):
        st.switch_page("app/pages/2_Browse_KCCs.py")
with c2:
    if st.button("Open evidence matrix"):
        st.switch_page("app/pages/5_Evidence_Matrix.py")
with c3:
    if st.button("API & downloads"):
        st.switch_page("app/pages/8_API_Downloads.py")

stat_cols = st.columns(6)
for col, (val, label) in zip(
    stat_cols,
    [
        (len(kccs), "Key characteristics"),
        (len(agents), "Agents"),
        (group1, "IARC Group 1"),
        (list_assays_count(), "Mapped assays"),
        (list_references_count(), "Source references"),
        ("CC-BY", "License"),
    ],
):
    with col:
        st.markdown(f'<p class="brand-serif" style="font-size:2rem;margin:0">{val}</p>', unsafe_allow_html=True)
        st.caption(label)

st.markdown("---")
st.markdown('<p class="eyebrow">The framework</p>', unsafe_allow_html=True)
st.markdown("#### The ten key characteristics")
if search_q:
    st.caption(f"Filtering overview highlights by `{search_q}`.")
preview_kccs = [
    k
    for k in kccs
    if not search_q
    or search_q in k["title"].lower()
    or search_q in k["short"].lower()
    or search_q in k.get("description", "").lower()
    or search_q in k.get("mechanism", "").lower()
]
cols = st.columns(4)
for i, k in enumerate(preview_kccs):
    s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
    with cols[i % 4]:
        with st.container(border=True):
            g_left, g_right = st.columns([1, 4])
            with g_left:
                # No branch on `is_extended`: the four extended characteristics
                # became Layer 2 candidate domains, and no KCC may carry that
                # flag any more (tests/test_candidate_domains.py enforces it).
                # The teal glyph and the "New addition" caption were unreachable.
                render_glyph(k["icon"], size=22, color=THEME["accent"])
            with g_right:
                st.caption(f"{k['n']:02d}")
                st.markdown(f"**{k['title']}**")
                st.caption(f"{s['carc_count']} agents (positive, ev ≥ 2) · {s['assay_count']} assays")
                if st.button("Open", key=f"ov_kcc_{k['id']}", use_container_width=True):
                    st.session_state["kcc_id"] = k["id"]
                    st.query_params["kcc_id"] = k["id"]
                    st.switch_page("app/pages/2a_KCC_Detail.py")
if not preview_kccs:
    st.caption("No KCCs match the current search.")

st.markdown("---")

# Featured agents.
#
# Derived from the data rather than a hard-coded id list: agent ids change when
# a source import lands (benzene became `benzene-iarc`), and a stale list
# silently renders an empty section. Ranking by evidence coverage then weight
# surfaces the best-documented agents and cannot rot the way a literal list does.
FEATURED_COUNT = 6
enriched, _ = agents_with_evidence()
by_id = {a["id"]: a for a in enriched}
shorts = [k["short"] for k in kccs]


def _scores_of(agent: dict) -> dict[str, int]:
    ev = agent.get("evidence", {})
    if isinstance(ev, list):
        return {e["kcc_id"]: e["score"] for e in ev}
    return ev or {}


def _matches_search(agent: dict) -> bool:
    if not search_q:
        return True
    hay = " ".join(
        [
            agent.get("name", ""),
            agent.get("cas", "") or "",
            agent.get("agent_type", ""),
            agent.get("iarc_group", "") or "",
            " ".join(agent.get("sites", [])),
        ]
    ).lower()
    return search_q in hay


def _rank_key(agent: dict) -> tuple[int, int, int, str]:
    """Rank on counts at successive thresholds, never on a sum.

    The 0-4 scale is ordinal, so adding scores is not meaningful; comparing how
    many characteristics clear each bar is. Breadth first, then strength.
    """
    scores = _scores_of(agent)
    return (
        kcc_coverage(scores),  # characteristics with limited evidence or better
        count_at_least(scores, 3),  # ... of which substantial or better
        count_at_least(scores, 4),  # ... of which convincing
        agent.get("name", ""),
    )


# Unfiltered ranking backs the worked example below, so it stays stable while
# the user types in the search box; the featured cards use the filtered view.
ranked_all = sorted((a for a in enriched if has_evidence(_scores_of(a))), key=_rank_key, reverse=True)
featured = [a for a in ranked_all if _matches_search(a)][:FEATURED_COUNT]

st.markdown('<p class="eyebrow">Featured</p>', unsafe_allow_html=True)
st.markdown("#### Best-documented agents")
st.caption(
    "Ranked by how many key characteristics carry evidence, then by how many reach "
    "substantial or convincing. Scores are ordinal, so they are counted, not summed. "
    "Scores come from two sources with different derivations, so this ranking mixes scales — "
    "the source is shown on each card."
)

for a in featured:
    fid = a["id"]
    ev = _scores_of(a)
    scores = [ev.get(k["id"]) for k in kccs]
    dirs = a.get("directions") or {}
    directions = [dirs.get(k["id"]) for k in kccs]
    cov = kcc_coverage(ev)
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 2])
        with c1:
            _tracks = {"10yr-iarc": "10-yr retrospective", "vol100-kc": "Volume 100"}
            st.markdown(f"**{a['name']}** · {a.get('iarc_group') or '—'} · {a.get('agent_type', '')}")
            st.caption(f"Evidence source: {_tracks.get(a.get('source_track'), 'unknown')}")
            cas = a.get("cas") or "—"
            if cas not in (None, "—"):
                st.caption(f"CAS {cas}")
        with c2:
            st.caption("Coverage")
            st.markdown(f"**{cov}/{len(kccs)}**")
        with c3:
            components.html(fingerprint_html(scores, shorts, directions=directions), height=24)
        if st.button(f"View {a['name']} →", key=f"feat_{fid}"):
            st.session_state["agent_id"] = fid
            st.query_params["agent_id"] = fid
            st.switch_page("app/pages/4_Agent_Detail.py")
if not featured:
    st.caption("No agents with scored evidence match the current search.")

st.markdown("---")

# Recent literature
refs_all = list_literature_references()
if search_q:
    refs_all = [
        r
        for r in refs_all
        if search_q
        in " ".join(
            [
                r.get("title", ""),
                r.get("authors", ""),
                r.get("journal", ""),
                " ".join(r.get("tags", [])),
            ]
        ).lower()
    ]
refs = refs_all[:5]
st.markdown('<p class="eyebrow">Recent</p>', unsafe_allow_html=True)
st.markdown("#### Methodology & literature")
for ref in refs:
    with st.container(border=True):
        tag = ", ".join(ref.get("tags", [])) or "Reference"
        st.markdown(
            f'<span style="color:{THEME["accent"]};font-family:JetBrains Mono,monospace;'
            f'font-size:0.7rem">{ref.get("year", "—")}</span> · {tag}',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{ref['title']}**")
        st.caption(f"{ref['authors']} — _{ref['journal']}_")
        if st.button("Open literature", key=f"ref_{ref['id']}"):
            st.switch_page("app/pages/7_Literature.py")
if not refs:
    st.caption("No recent literature matches the current search.")

st.markdown("---")

# Evidence explainer. The worked example is the best-documented agent in the
# database rather than a hard-coded id, so it always shows a real fingerprint —
# and its label comes from the row itself, never from a constant that can drift.
example = next(iter(ranked_all), None)
example_ev = _scores_of(example) if example else {}
example_scores = [example_ev.get(k["id"]) for k in kccs]
example_dirs = (example or {}).get("directions") or {}
example_directions = [example_dirs.get(k["id"]) for k in kccs]
example_substantial = count_at_least(example_ev, 3)
example_assessed = len(example_ev)

# Read from the data, never written as literals: the "how to read this" text
# described only one of the two tracks and claimed a score of 0 could mean "no
# evaluation", which contradicts how the rest of the app treats a missing cell.
_track_counts = evidence_track_counts()
n_tenyr = _track_counts.get("10yr-iarc", 0)
n_vol100 = _track_counts.get("vol100-kc", 0)
n_possible = len(agents) * len(kccs)
n_unassessed = n_possible - sum(_track_counts.values())

left, right = st.columns(2)
with left:
    st.markdown('<p class="eyebrow">How to read this</p>', unsafe_allow_html=True)
    st.markdown("#### Every cell is derived from a published source table, not scored by hand.")
    st.write(
        f"Scores come from **two IARC sources**, each with its own documented rule. "
        f"**{n_tenyr} cells** come from the 10-year retrospective (Rusyn et al. 2024): either the "
        f"standardized strength label that paper assigned to the pair, or — where it assigned "
        f"none — the number of primary model systems reporting a positive call. "
        f"**{n_vol100} cells** come from the Volume 100 Group 1 re-review (Krewski et al. 2019), "
        f"where the score reflects how many of the four source types Figure 22.4 shades."
    )
    st.write(
        f"**A score of 0 is a finding, not a blank.** It means the pair was assessed and the "
        f"primary systems were negative, or that positive calls appeared only in supplementary "
        f"systems. A pair that was never assessed carries **no cell at all**: "
        f"{n_unassessed:,} of the {n_possible:,} possible pairs are omitted from the API, left "
        f"empty in CSV exports and marked *not assessed* in every figure."
    )
    st.write(
        "Every cell records its track and its derivation, so any score traces back to a specific "
        "row of the source publication. The two tracks are **not interchangeable** — the same "
        "number carries different meaning under each rule, so compare within a track rather "
        "than across. See the methodology page for both derivations in full."
    )
with right:
    components.html(ev_legend_html(), height=48)
    if example:
        with st.container(border=True):
            st.caption(f"EXAMPLE · {example['name'].upper()}")
            components.html(fingerprint_html(example_scores, shorts, directions=example_directions), height=28)
            st.caption(
                f"{example_assessed} of {len(kccs)} characteristics assessed · "
                f"{example_substantial} substantial or better"
            )
