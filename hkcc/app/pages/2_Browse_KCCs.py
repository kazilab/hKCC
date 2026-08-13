"""Browse KCCs."""

import streamlit as st

from hkcc.app.components.glyphs import render_glyph
from hkcc.app.data_client import kcc_stats, list_candidate_domains, list_kccs
from hkcc.app.page_shell import global_search_query, init_page

THEME, _ = init_page("kccs")

if st.query_params.get("kcc_id"):
    st.session_state["kcc_id"] = st.query_params["kcc_id"]
    st.switch_page("app/pages/2a_KCC_Detail.py")

kccs = list_kccs()
stats = kcc_stats()
q_default = global_search_query()

st.markdown('<p class="mono">The framework</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">The ten key characteristics</h1>', unsafe_allow_html=True)
st.caption("Each KCC describes a distinct biological process consistently observed in established carcinogens.")

q = st.text_input(
    "Search KCCs",
    value=q_default,
    placeholder="Search title, short label, mechanism…",
    label_visibility="collapsed",
    key="kcc_search",
)
if q != q_default:
    st.query_params["q"] = q
    st.rerun()

filtered = kccs

if q:
    ql = q.lower()
    filtered = [
        k
        for k in filtered
        if ql in k["title"].lower()
        or ql in k["short"].lower()
        or ql in k.get("description", "").lower()
        or ql in k.get("mechanism", "").lower()
    ]

if not filtered:
    st.info("No KCCs match the current filters.")
    st.stop()

view = st.radio("View", ["Grid", "List"], horizontal=True, label_visibility="collapsed")

if view == "Grid":
    cols = st.columns(2)
    for i, k in enumerate(filtered):
        s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
        color = THEME["accent"]
        with cols[i % 2]:
            with st.container(border=True):
                g1, g2 = st.columns([1, 8])
                with g1:
                    render_glyph(k["icon"], size=26, color=color)
                with g2:
                    st.caption(f"KCC-{k['n']:02d}")
                    st.markdown(f"### {k['title']}")
                    st.write(k["description"])
                    st.caption(f"{s['carc_count']} agents (positive, ev ≥ 2) · {s['assay_count']} assays")
                    if st.button("Open detail →", key=f"kcc_open_{k['id']}", use_container_width=True):
                        st.session_state["kcc_id"] = k["id"]
                        st.query_params["kcc_id"] = k["id"]
                        st.switch_page("app/pages/2a_KCC_Detail.py")
else:
    rows = []
    for k in filtered:
        s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
        rows.append(
            {
                "ID": f"KCC-{k['n']:02d}",
                "Title": k["title"],
                "Short": k["short"],
                "Agents (positive, ev ≥ 2)": s["carc_count"],
                "Assays": s["assay_count"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    pick = st.selectbox(
        "Open KCC detail",
        options=filtered,
        format_func=lambda k: f"KCC-{k['n']:02d}: {k['title']}",
    )
    if pick and st.button("View KCC detail →", type="primary"):
        st.session_state["kcc_id"] = pick["id"]
        st.query_params["kcc_id"] = pick["id"]
        st.switch_page("app/pages/2a_KCC_Detail.py")


# ── Layer 2: candidate domains ───────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="eyebrow">Layer 2 · candidate annotations</p>', unsafe_allow_html=True)
st.markdown("#### Cross-cutting mechanistic domains")
st.caption(
    "These are **not** key characteristics. Each qualifies how an observation arose and parents "
    "onto one or more of the ten KCCs above. They carry no score of their own: an observation is "
    "counted once, against its KCC."
)

domains = list_candidate_domains()

# The evidence bars are aspirational, not enforceable. `assay_annotations` holds
# no dose, duration, route, comparator, cytotoxicity or replication, so a bar
# reading "at non-cytotoxic concentrations" cannot be checked against anything
# in this database. Saying so is the difference between a candidate set and a
# validated one.
st.warning(
    "**Provisional.** These domains and their assay mappings are proposals, not validated "
    "evidence. The listed assays are *candidate* readouts: the database records no dose, "
    "duration, route, comparator, cytotoxicity or replication, so the dose/time and "
    "non-cytotoxicity conditions written into the evidence bars below cannot yet be "
    "enforced. Every domain's `status` is `candidate` for this reason."
)

kcc_short = {k["id"]: k["short"] for k in kccs}
_levels = {"functional": "functional", "descriptive": "descriptive (does not meet a functional bar)"}
for d in domains:
    with st.container(border=True):
        st.markdown(f"**{d['code']} · {d['title']}**")
        st.write(d["definition"])
        prim = ", ".join(kcc_short.get(i, i) for i in d["primary_kcc_ids"]) or "—"
        sec = ", ".join(kcc_short.get(i, i) for i in d["secondary_kcc_ids"])
        st.caption(f"Primary KCCs: {prim}" + (f"  ·  Secondary: {sec}" if sec else ""))
        if not d.get("assay_links"):
            st.caption("⚠ No candidate assays mapped yet — the evidence bar has nothing to apply to.")
        with st.expander("Evidence bar and exclusions"):
            st.markdown(f"**Minimum evidence.** {d['minimum_evidence']}")
            st.markdown(f"**Does not qualify.** {d['key_exclusions']}")
            if d.get("assay_links"):
                st.markdown("**Candidate assays.**")
                for link in d["assay_links"]:
                    level = _levels.get(link.get("evidence_level"), link.get("evidence_level") or "unclassified")
                    st.caption(f"`{link['assay_id']}` — {level}")
