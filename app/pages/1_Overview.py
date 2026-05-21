"""Overview — mockup screen 1."""

import streamlit as st
import streamlit.components.v1 as components

from app.components.glyphs import render_glyph
from app.data_client import (
    agents_with_evidence,
    kcc_stats,
    list_agents,
    list_assays_count,
    list_kccs,
    list_references,
    list_references_count,
)
from app.page_shell import global_search_query, init_page
from app.utils.evidence import ev_legend_html, fingerprint_html, kcc_coverage, total_evidence

THEME, _ = init_page("overview")

kccs = list_kccs()
agents = list_agents()
stats = kcc_stats()
group1 = sum(1 for a in agents if a.get("iarc_group") == "1")
search_q = global_search_query().strip().lower()

st.markdown('<span class="mono">Live · hKCC</span>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display">A mechanistic atlas for the '
    f'<em style="font-style:italic;color:{THEME["accent"]}">14 key characteristics</em> '
    "of human carcinogens.</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="lede">hKCC is an open, curated database that organises mechanistic evidence '
    "linking known and suspected carcinogens to the key characteristics framework proposed by "
    "Smith et al. (2016) and extended in the years since.</p>",
    unsafe_allow_html=True,
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
        (len(agents), "Curated agents"),
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
st.markdown("#### Fourteen key characteristics")
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
                render_glyph(
                    k["icon"],
                    size=22,
                    color=THEME["accent"] if not k["is_extended"] else THEME["teal"],
                )
            with g_right:
                st.caption(f"{k['n']:02d}")
                st.markdown(f"**{k['title']}**")
                st.caption(f"{s['carc_count']} agents · {s['assay_count']} assays")
                if k["is_extended"]:
                    st.caption("New addition")
                if st.button("Open", key=f"ov_kcc_{k['id']}", use_container_width=True):
                    st.query_params["kcc_id"] = k["id"]
                    st.switch_page("app/pages/2a_KCC_Detail.py")
if not preview_kccs:
    st.caption("No KCCs match the current search.")

st.markdown("---")

# Featured agents
FEATURED = ["tobacco-smoke", "benzene", "asbestos", "tcdd", "ethanol", "arsenic"]
enriched, _ = agents_with_evidence()
by_id = {a["id"]: a for a in enriched}
shorts = [k["short"] for k in kccs]

st.markdown('<p class="eyebrow">Featured</p>', unsafe_allow_html=True)
st.markdown("#### Most-queried agents this week")
featured_ids = []
for fid in FEATURED:
    a = by_id.get(fid)
    if not a:
        continue
    hay = " ".join(
        [
            a.get("name", ""),
            a.get("cas", ""),
            a.get("agent_type", ""),
            a.get("iarc_group", ""),
            " ".join(a.get("sites", [])),
        ]
    ).lower()
    if search_q and search_q not in hay:
        continue
    featured_ids.append(fid)

for fid in featured_ids:
    a = by_id[fid]
    ev = a.get("evidence", {})
    if isinstance(ev, list):
        ev = {e["kcc_id"]: e["score"] for e in ev}
    scores = [ev.get(k["id"], 0) for k in kccs]
    cov = kcc_coverage(ev)
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 2])
        with c1:
            st.markdown(f"**{a['name']}** · {a.get('iarc_group', '—')} · {a.get('agent_type', '')}")
            cas = a.get("cas", "—")
            if cas not in (None, "—"):
                st.caption(f"CAS {cas}")
        with c2:
            st.caption("Coverage")
            st.markdown(f"**{cov}/14**")
        with c3:
            components.html(fingerprint_html(scores, shorts), height=24)
        if st.button(f"View {a['name']} →", key=f"feat_{fid}"):
            st.query_params["agent_id"] = fid
            st.switch_page("app/pages/4_Agent_Detail.py")
if not featured_ids:
    st.caption("No featured agents match the current search.")

st.markdown("---")

# Recent literature
refs_all = list_references()
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

# Evidence explainer
benzene = by_id.get("benzene")
benz_ev = benzene.get("evidence", {}) if benzene else {}
if isinstance(benz_ev, list):
    benz_ev = {e["kcc_id"]: e["score"] for e in benz_ev}
benz_scores = [benz_ev.get(k["id"], 0) for k in kccs]
benz_weight = total_evidence(benz_ev) if benzene else 0

left, right = st.columns(2)
with left:
    st.markdown('<p class="eyebrow">How to read this</p>', unsafe_allow_html=True)
    st.markdown("#### Every cell in hKCC is an editorial judgement of evidence strength.")
    st.write(
        "For each carcinogen × KCC pair, curators score the weight of mechanistic evidence on a "
        "0–4 ordinal scale, drawing on IARC monograph mechanistic write-ups, primary literature, "
        "and high-throughput screening data from ToxCast / Tox21 where available."
    )
    st.write(
        "Hover any cell in the evidence matrix to see the underlying citations. "
        "Scoring is fully transparent and versioned."
    )
with right:
    components.html(ev_legend_html(), height=48)
    with st.container(border=True):
        st.caption("EXAMPLE · BENZENE")
        components.html(fingerprint_html(benz_scores, shorts), height=28)
        st.caption(f"14 cells · 1 row · {benz_weight}/56 weighted score")
