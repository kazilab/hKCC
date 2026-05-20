"""Agent profile — mockup screen 5."""

import streamlit as st

from app.components.radar import render_radar
from app.data_client import agent_evidence_map, get_agent, list_kccs, list_references
from app.theme import HKCC_CSS, THEME
from app.utils.evidence import EV_COLORS, kcc_coverage, total_evidence

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

agent_id = st.query_params.get("agent_id") or st.session_state.get("agent_id")
if not agent_id:
    st.warning("Select an agent from the Carcinogens page.")
    if st.button("← Browse carcinogens"):
        st.switch_page("app/pages/3_Carcinogens.py")
    st.stop()

agent = get_agent(agent_id)
if not agent:
    st.error("Agent not found.")
    st.stop()

kccs = list_kccs()
ev_map = agent_evidence_map(agent, [k["id"] for k in kccs])
cov = kcc_coverage(ev_map)
weight = total_evidence(ev_map)
max_score = len(kccs) * 4
n_refs = sum(e.get("n_refs", 0) for e in agent.get("evidence", []) if isinstance(agent.get("evidence"), list))

if st.button("← All agents"):
    st.switch_page("app/pages/3_Carcinogens.py")

st.caption(f"{agent.get('iarc_group', '—')} · {agent['agent_type']}" + (f" · CAS {agent['cas']}" if agent.get("cas") not in (None, "—") else ""))
st.markdown(f'<h1 class="h-display">{agent["name"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="lede">{agent["summary"]}</p>', unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4)
s1.metric("KCC coverage (ev ≥ 2)", f"{cov}/14")
s2.metric("Total weighted score", f"{weight}/{max_score}")
s3.metric("Tumour sites", len(agent.get("sites", [])))
s4.metric("Curated references", n_refs or "—")

tab = st.tabs(["KCC fingerprint", "Detailed evidence", "Tumour sites", "References"])

with tab[0]:
    left, right = st.columns(2)
    with left:
        st.markdown("**Radar plot**")
        render_radar(kccs, ev_map)
    with right:
        st.markdown("**All 14 KCCs**")
        for k in kccs:
            v = ev_map.get(k["id"], 0)
            bar = "".join(
                f'<span style="display:inline-block;width:18px;height:8px;background:{EV_COLORS.get(i, EV_COLORS[0])};'
                f'opacity:{1 if i <= v else 0.2};margin-right:2px;border-radius:1px"></span>'
                for i in range(4)
            )
            st.markdown(
                f'<div style="display:grid;grid-template-columns:40px 1fr 120px;gap:8px;align-items:center;'
                f'padding:8px 0;border-bottom:1px solid {THEME["rule"]}">'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:10px">{k["n"]:02d}</span>'
                f'<span>{k["short"]}</span>{bar}</div>',
                unsafe_allow_html=True,
            )

with tab[1]:
    for k in kccs:
        v = ev_map.get(k["id"], 0)
        if v < 1:
            continue
        with st.container(border=True):
            st.markdown(f"#### {k['title']}")
            st.progress(v / 4.0)
            st.write(k["mechanism"])
            st.caption(f"Score {v}/4 · anchored to curated references")

with tab[2]:
    for site in agent.get("sites", []):
        with st.container(border=True):
            st.markdown(f"**{site}**")
            st.caption("Sufficient evidence in humans (IARC monograph)")

with tab[3]:
    refs = list_references()
    for ref in refs[:10]:
        st.markdown(f"**{ref['year']}** · {ref['title']}")
        st.caption(f"{ref['authors']} · _{ref['journal']}_ · {ref.get('citations', 0)} cites")
