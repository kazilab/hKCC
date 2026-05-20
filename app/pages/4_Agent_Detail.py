"""Agent profile — mockup screen 5."""

import streamlit as st

from app.components.radar import render_radar
from app.data_client import agent_evidence_map, evidence_for_agent, get_agent, list_kccs
from app.page_shell import init_page
from app.theme import EV_COLORS
from app.utils.evidence import kcc_coverage, total_evidence

THEME, _ = init_page("agent_detail")

agent_id = st.query_params.get("agent_id") or st.session_state.get("agent_id")
if isinstance(agent_id, list):
    agent_id = agent_id[0] if agent_id else None
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
kcc_by_id = {k["id"]: k for k in kccs}
ev_map = agent_evidence_map(agent, [k["id"] for k in kccs])
evidence_rows = evidence_for_agent(agent_id)
cov = kcc_coverage(ev_map)
weight = total_evidence(ev_map)
max_score = len(kccs) * 4
n_refs = sum(e["n_refs"] for e in evidence_rows)

if st.button("← All agents"):
    st.switch_page("app/pages/3_Carcinogens.py")

st.caption(
    f"{agent.get('iarc_group', '—')} · {agent['agent_type']}"
    + (f" · CAS {agent['cas']}" if agent.get("cas") not in (None, "—") else "")
)
st.markdown(f'<h1 class="h-display">{agent["name"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="lede">{agent["summary"]}</p>', unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4)
s1.metric("KCC coverage (ev ≥ 2)", f"{cov}/14")
s2.metric("Total weighted score", f"{weight}/{max_score}")
s3.metric("Tumour sites", len(agent.get("sites", [])))
s4.metric("Curated references", n_refs or "—")

tab = st.tabs(["KCC fingerprint", "Detailed evidence", "Tumour sites", "All references"])

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
    for cell in evidence_rows:
        if cell["score"] < 1:
            continue
        k = kcc_by_id.get(cell["kcc_id"])
        if not k:
            continue
        with st.expander(f"KCC-{k['n']:02d}: {k['title']} · score {cell['score']}/4", expanded=False):
            st.progress(cell["score"] / 4.0)
            st.write(k["mechanism"])
            n = cell["n_refs"]
            st.caption(f"Anchored to {n} curated reference{'s' if n != 1 else ''}")
            for ref in cell.get("refs", []):
                st.markdown(f"**{ref.get('year', '—')}** · {ref['title']}")
                st.caption(f"{ref['authors']} · _{ref['journal']}_")
                if ref.get("doi") and ref["doi"] != "—":
                    doi = ref["doi"].replace("https://doi.org/", "")
                    st.markdown(f"[DOI](https://doi.org/{doi})")

with tab[2]:
    for site in agent.get("sites", []):
        with st.container(border=True):
            st.markdown(f"**{site}**")
            st.caption("Sufficient evidence in humans (IARC monograph)")

with tab[3]:
    seen: set[str] = set()
    for cell in evidence_rows:
        for ref in cell.get("refs", []):
            if ref["id"] in seen:
                continue
            seen.add(ref["id"])
            st.markdown(f"**{ref.get('year', '—')}** · {ref['title']}")
            st.caption(f"{ref['authors']} · _{ref['journal']}_")
