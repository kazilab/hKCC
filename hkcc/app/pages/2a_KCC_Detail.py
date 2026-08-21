"""KCC detail."""

import streamlit as st

from hkcc.app.components.card import card
from hkcc.app.components.embed import html_block
from hkcc.app.components.glyphs import render_glyph
from hkcc.app.data_client import (
    agents_for_kcc,
    assays_for_kcc,
    framework_references,
    get_kcc,
    kcc_stats,
    references_for_kcc,
)
from hkcc.app.page_shell import init_page
from hkcc.app.utils.evidence import ev_bar_html, group_chip_html

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

color = THEME["accent"]
set_label = "Established KCC (Smith et al. 2016)"
chip = (
    f'<span style="font-size:10px;padding:3px 8px;border:1px solid {THEME["rule"]};'
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
    with card("kcc-symbol"):
        render_glyph(k["icon"], size=64, color=color)
        st.caption("SYMBOL")

stats = kcc_stats()
s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
linked = agents_for_kcc(kcc_id, min_score=2)
rel_assays = assays_for_kcc(kcc_id)
rel_refs = references_for_kcc(kcc_id)

c1, c2, c3 = st.columns(3)
c1.metric(
    "Agents w/ evidence",
    s["carc_count"],
    help="Agents with positive evidence scoring 2 or more for this characteristic.",
)
c2.metric("Mapped assays", s["assay_count"])
c3.metric("Anchor references", len(rel_refs))

st.markdown("---")

mech_l, mech_r = st.columns(2)
with mech_l:
    st.markdown('<p class="eyebrow">Mechanism</p>', unsafe_allow_html=True)
    st.markdown("#### How agents express this characteristic")
    st.write(k["mechanism"])
    st.caption(
        "Demonstration of this characteristic alone is not sufficient to classify an agent "
        "as carcinogenic; the framework aggregates signals across all ten KCCs."
    )
with mech_r:
    st.markdown('<p class="eyebrow">Strongest evidence</p>', unsafe_allow_html=True)
    st.markdown("#### Agents scoring highest for this characteristic")
    top = sorted(linked, key=lambda a: a.get("kcc_score", 0), reverse=True)[:6]
    if top:
        for a in top:
            st.markdown(f"- **{a['name']}** · {a.get('kcc_score', 0)}/4")
    else:
        st.caption("No agent reaches a score of 2 for this characteristic.")

st.markdown("---")
st.markdown(f"#### Linked carcinogens with evidence ≥ 2 for {k['short']} ({len(linked)})")
if linked:
    for i, row in enumerate(linked):
        with card(f"kcc-linked-{i}"):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**{row['name']}**")
                html_block(group_chip_html(row.get("iarc_group")))
                st.caption(row.get("agent_type", ""))
            with c2:
                html_block(ev_bar_html(row["kcc_score"]))
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
    for i, a in enumerate(rel_assays):
        with card(f"kcc-assay-{i}"):
            st.markdown(f"**{a['name']}**")
            st.caption(f"{a['type']} · {a['target']} · {a['throughput']}")
            if a.get("oecd_tg") and a["oecd_tg"] != "—":
                st.caption(a["oecd_tg"])
else:
    st.caption("No assays mapped to this KCC yet.")

st.markdown("---")
from hkcc.app.components.ref_card import render_ref_cards  # noqa: E402

# Two different things, previously merged under one heading. `reference_kccs`
# holds no rows, so every KCC page listed the same framework papers as if they
# anchored that characteristic.
st.markdown(f"#### Anchoring publications ({len(rel_refs)})")
if rel_refs:
    render_ref_cards(rel_refs[:12], height=min(700, 100 + len(rel_refs[:12]) * 100))
else:
    st.caption(
        "**No publications are linked to this characteristic.** Per-KCC reference links "
        "(`reference_kccs`) are not populated in this release, so nothing here is anchored "
        "to KCC-specific literature. Evidence citations live on each agent's cells instead."
    )

_framework = framework_references()
if _framework:
    st.markdown(f"#### Framework & methodology references ({len(_framework)})")
    st.caption(
        "General literature for the project as a whole — the KCC framework, the source "
        "publications and their methods. **Not** evidence for this characteristic; the same "
        "list appears on every KCC page."
    )
    render_ref_cards(_framework[:12], height=min(700, 100 + len(_framework[:12]) * 100))
