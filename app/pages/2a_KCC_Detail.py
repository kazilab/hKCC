"""KCC detail — mockup ScreenKCCDetail."""

import streamlit as st
import streamlit.components.v1 as components

from app.components.glyphs import render_glyph
from app.data_client import (
    agents_for_kcc,
    assays_for_kcc,
    get_kcc,
    kcc_stats,
    references_for_kcc,
)
from app.page_shell import init_page
from app.utils.evidence import ev_bar_html, group_chip_html

THEME, _ = init_page("kcc_detail")

kcc_id = st.query_params.get("kcc_id") or st.session_state.get("kcc_id")
if isinstance(kcc_id, list):
    kcc_id = kcc_id[0] if kcc_id else None

if not kcc_id:
    st.warning("Select a KCC from Browse KCCs.")
    if st.button("← Browse KCCs"):
        st.switch_page("app/pages/2_Browse_KCCs.py")
    st.stop()

k = get_kcc(kcc_id)
if not k:
    st.error("KCC not found.")
    st.stop()

st.session_state["hkcc_detail_title"] = f"KCC-{k['n']:02d}"

if st.button("← All KCCs"):
    st.switch_page("app/pages/2_Browse_KCCs.py")

color = THEME["teal"] if k["is_extended"] else THEME["accent"]
set_label = "Extended set" if k["is_extended"] else "Original (Smith 2016)"
chip = (
    f'<span style="font-size:10px;padding:3px 8px;border:1px solid {THEME["teal"] if k["is_extended"] else THEME["rule"]};'
    f'border-radius:3px;color:{color}">{set_label}</span>'
)

head_l, head_r = st.columns([4, 1])
with head_l:
    st.markdown(
        f'<span class="mono" style="color:{color}">KCC-{k["n"]:02d}</span> {chip}',
        unsafe_allow_html=True,
    )
    st.markdown(f'<h1 class="h-display" style="font-size:2.5rem">{k["title"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="lede">{k["description"]}</p>', unsafe_allow_html=True)
with head_r:
    with st.container(border=True):
        render_glyph(k["icon"], size=64, color=color)
        st.caption("SYMBOL")

stats = kcc_stats()
s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
linked = agents_for_kcc(kcc_id, min_score=2)
rel_assays = assays_for_kcc(kcc_id)
rel_refs = references_for_kcc(kcc_id)
examples = k.get("examples", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Agents w/ evidence", s["carc_count"])
c2.metric("Mapped assays", s["assay_count"])
c3.metric("Anchor references", len(rel_refs))
c4.metric("Canonical examples", len(examples))

st.markdown("---")

mech_l, mech_r = st.columns(2)
with mech_l:
    st.markdown('<p class="eyebrow">Mechanism</p>', unsafe_allow_html=True)
    st.markdown("#### How agents express this characteristic")
    st.write(k["mechanism"])
    st.caption(
        "Demonstration of this characteristic alone is not sufficient to classify an agent "
        "as carcinogenic; the framework aggregates signals across all 14 KCCs."
    )
with mech_r:
    st.markdown('<p class="eyebrow">Canonical agents</p>', unsafe_allow_html=True)
    st.markdown("#### Frequently cited examples")
    if examples:
        for ex in examples:
            st.markdown(f"- **{ex}**")
    else:
        st.caption("No example list in the curated release.")

st.markdown("---")
st.markdown(f"#### Linked carcinogens with evidence ≥ 2 for {k['short']} ({len(linked)})")
if linked:
    for row in linked:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**{row['name']}**")
                components.html(group_chip_html(row.get("iarc_group")), height=28)
                st.caption(row.get("agent_type", ""))
            with c2:
                components.html(ev_bar_html(row["kcc_score"]), height=28)
            with c3:
                if st.button("Profile →", key=f"kcc_agent_{row['id']}"):
                    st.session_state["agent_id"] = row["id"]
                    st.query_params["agent_id"] = row["id"]
                    st.switch_page("app/pages/4_Agent_Detail.py")
else:
    st.caption("No agents with evidence ≥ 2 on this KCC.")

st.markdown("---")
st.markdown(f"#### Key assays ({len(rel_assays)})")
if rel_assays:
    for a in rel_assays:
        with st.container(border=True):
            st.markdown(f"**{a['name']}**")
            st.caption(f"{a['type']} · {a['target']} · {a['throughput']}")
            if a.get("oecd_tg") and a["oecd_tg"] != "—":
                st.caption(a["oecd_tg"])
else:
    st.caption("No assays mapped to this KCC yet.")

st.markdown("---")
st.markdown(f"#### Anchoring publications ({len(rel_refs)})")
if rel_refs:
    from app.components.ref_card import render_ref_cards

    render_ref_cards(rel_refs[:12], height=min(700, 100 + len(rel_refs[:12]) * 100))
else:
    st.caption("No references linked.")
