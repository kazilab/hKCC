"""IARC Monograph 10-year retrospective evidence matrix.

Renders the ``iarc_monograph_*`` tables, derived from Rusyn et al. 2024
Supplementary Files 12 + 14. Three filterable views:

1. **Per-agent heat-map** — 10 KCs × 8 model systems of Yes / Equivocal / No /
   Protective calls for the selected agent, plus the paper-aggregate Strong /
   Moderate / Weak chip per KC.
2. **Per-KCC roster** — agents that received a positive (or other) call for a
   chosen KC, with volume coverage.
3. **Source ladder** — links straight to the Rusyn 2024 PDF stored locally.

The whole page degrades to a static notice when no data source is available.
"""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from hkcc.app.components.card import card
from hkcc.app.data_client import (
    get_data_source,
    get_monograph_agent_matrix,
    list_kccs,
    list_monograph_agents,
    list_monograph_kcc_agents,
    list_monograph_volumes,
)
from hkcc.app.page_shell import init_page

init_page("iarc_matrix")

st.markdown('<p class="mono">Analyze · IARC Monograph matrix</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display" style="font-size:2rem">IARC 10-year KCC retrospective</h1>',
    unsafe_allow_html=True,
)
st.caption(
    "Per-(agent, KC, model system) Yes / No / Equivocal / Protective calls, as published in "
    "Rusyn et al. (2024), Toxicological Sciences 198(1):141-154 "
    "[doi:10.1093/toxsci/kfad134](https://doi.org/10.1093/toxsci/kfad134), covering IARC "
    "Monograph Volumes 112–130."
)
st.warning(
    "**These are the study authors' retrospective coding, not IARC Working Group "
    "determinations.** Rusyn and Wright coded the monograph content themselves to build a "
    "comparable cross-volume matrix. Only the *standardized strength* and *data role* fields "
    "(shown in the strength row below, and on Agent Detail) are extracted Working Group "
    "outputs. An hKCC score derived from these calls inherits that distinction."
)

if get_data_source() == "no_data":
    st.info(
        "The IARC Monograph matrix needs a backing database. Check that "
        "`hkcc.db` is present, or set `API_BASE_URL` to point at a running "
        "hKCC API."
    )
    st.stop()

volumes = list_monograph_volumes()
if not volumes:
    st.warning("This database contains no IARC Monograph rows.")
    st.stop()

monograph_agents = list_monograph_agents()

with card("iarc-matrix"):
    cols = st.columns(3)
    cols[0].metric("Volumes covered", len({v["volume"] for v in volumes}))
    # Counted from the call table. This read `len({v["volume"] for v in volumes})`
    # — the number of volumes again — so it reported 19 agents against 73.
    cols[1].metric("Agents with calls", len(monograph_agents))
    cols[2].metric("Span", f"{volumes[0]['year']}–{volumes[-1]['year']}")
    st.caption(
        "Each Monograph volume contributes a Yes/No/Equivocal cell per (model system × KC) for every agent it covers."
    )

tab_agent, tab_kc, tab_refs = st.tabs(["By agent", "By KC", "Source publication"])

# ── Tab 1: per-agent heat-map ───────────────────────────────────────────────
with tab_agent:
    # Membership comes from the call table itself. Filtering on `source_ref_id`
    # plus a hard-coded list of names hid 12 agents whose calls were present all
    # along (2mbt, tbbpa, tcab, parathion, ortho-nitroanisole and others), and
    # would have hidden every future import until someone edited the list.
    agent_choices = {f"{a['name']}  ·  {a.get('iarc_group') or '—'}": a["agent_id"] for a in monograph_agents}

    # Deep link from Agent Detail (?iarc_agent=<id>), which sends readers here
    # for the call-level evidence behind a 0 or protective score. The selectbox
    # is keyed, so its stored label wins over `index` — set the label directly.
    requested = st.query_params.get("iarc_agent")
    if isinstance(requested, list):
        requested = requested[0] if requested else None
    if requested:
        for _label, _aid in agent_choices.items():
            if _aid == requested:
                st.session_state["iarc_matrix_agent"] = _label
                break
        del st.query_params["iarc_agent"]

    label = st.selectbox(
        "Agent",
        options=list(agent_choices.keys()),
        index=0 if agent_choices else None,
        key="iarc_matrix_agent",
    )
    if not label:
        st.caption("No agent selected.")
    else:
        aid = agent_choices[label]
        matrix = get_monograph_agent_matrix(aid)
        if not matrix or not matrix.get("calls"):
            st.info(
                "This agent has no rows in the Rusyn 2024 matrix. "
                "Try one of the agents listed in IARC Monograph Vol 112–130."
            )
        else:
            kccs = sorted(list_kccs() or [], key=lambda k: k["n"])
            kc_ids = [k["id"] for k in kccs if k["n"] <= 10]
            model_systems = [
                "Exposed Humans",
                "Human cells in vitro",
                "Mammalian in vivo",
                "Mammalian in vitro",
                "Other in vivo",
                "Other in vitro",
                "ToxCast data",
                "ToxRefDB data",
            ]
            grid = []
            for ms in model_systems:
                row = {"Model system": ms}
                for kc_id in kc_ids:
                    cell = matrix["calls"].get(kc_id, {}).get(ms, "")
                    row[kc_id.replace("kcc-", "KC")] = cell
                grid.append(row)
            df = pd.DataFrame(grid)
            # Strength row
            strength_row = {"Model system": "Standardized strength (paper)"}
            for kc_id in kc_ids:
                s = matrix.get("strength", {}).get(kc_id) or {}
                strength_row[kc_id.replace("kcc-", "KC")] = s.get("label") or ""
            df = pd.concat([df, pd.DataFrame([strength_row])], ignore_index=True)

            def _style_cell(val: object) -> str:
                v = str(val or "").strip()
                color_map = {
                    "Yes": "#163",
                    "No": "#7c8a90",
                    "Equivocal": "#a86b00",
                    "Protective": "#0a6cb8",
                    "Strong": "#163",
                    "Moderate": "#a86b00",
                    "Weak": "#7c8a90",
                }
                bg_map = {
                    "Yes": "#d6ead7",
                    "No": "#eceff1",
                    "Equivocal": "#fff2d6",
                    "Protective": "#d3e7f5",
                    "Strong": "#d6ead7",
                    "Moderate": "#fff2d6",
                    "Weak": "#eceff1",
                }
                if v in color_map:
                    return f"background-color: {bg_map[v]}; color: {color_map[v]}; font-weight: 600"
                return ""

            styled = df.style.map(_style_cell, subset=[c for c in df.columns if c != "Model system"])
            st.dataframe(styled, hide_index=True, use_container_width=True)
            with st.expander("Per-volume Overall strength"):
                per_vol = matrix.get("overall_strength_per_volume", {})
                if not per_vol:
                    st.caption("No per-volume strength row in the source data for this agent.")
                else:
                    rows = []
                    for vol, kc_map in sorted(per_vol.items()):
                        row = {"Volume": vol}
                        for kc_id in kc_ids:
                            row[kc_id.replace("kcc-", "KC")] = kc_map.get(kc_id, "")
                        rows.append(row)
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            st.caption(f"Covered in Monograph Vol(s): {', '.join(matrix.get('monograph_volumes', []))}.")

# ── Tab 2: agents per KC ─────────────────────────────────────────────────────
with tab_kc:
    kccs = sorted(list_kccs() or [], key=lambda k: k["n"])
    kc_choice = st.selectbox(
        "KC",
        options=[k for k in kccs if k["n"] <= 10],
        index=0,
        format_func=lambda k: f"KC{k['n']}: {k['title']}",
    )
    call_choice = st.radio(
        "Call",
        options=["Yes", "Equivocal", "No", "Protective"],
        horizontal=True,
        index=0,
    )
    rows = list_monograph_kcc_agents(kc_choice["id"], call=call_choice) if kc_choice else []
    st.caption(f"{len(rows)} agent(s) with **{call_choice}** for KC{kc_choice['n']}.")
    if rows:
        df = pd.DataFrame(
            [
                {
                    "Agent": r["agent_name"],
                    "IARC Monograph volumes": ", ".join(r["volumes"]),
                    "Volume count": r["n_calls"],
                }
                for r in rows
            ]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)

# ── Tab 3: source publication ────────────────────────────────────────────────
with tab_refs:
    st.markdown("### Rusyn et al. (2024)")
    st.markdown(
        "**Ten years of using key characteristics of human carcinogens to organize "
        "and evaluate mechanistic evidence in IARC Monographs Volumes 112–130: "
        "impact and lessons learned.**  \n"
        "_Toxicological Sciences_ 198(1):141–154."
    )
    doi = "10.1093/toxsci/kfad134"
    st.markdown(
        f'DOI: <a href="https://doi.org/{html.escape(doi)}" target="_blank" '
        f'rel="noopener noreferrer"><code>{html.escape(doi)}</code></a>',
        unsafe_allow_html=True,
    )
    # Pointing at a repo path is no use to a reader on the hosted app or a pip
    # install — docs/ ships in neither. Send them to the in-app rules instead.
    st.markdown(
        "The deterministic algorithm that maps these call cells to `evidence.score` "
        "is documented on the Methodology page."
    )
    if st.button("Open the scoring rules →", key="iarc_rules_link"):
        st.switch_page("app/pages/9a_Methodology.py")
