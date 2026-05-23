"""IARC Monograph 10-year retrospective evidence matrix.

Renders the data ingested by ``pipelines.import_10yr_kcc`` from Rusyn et al.
2024 Supplementary Files 12 + 14. Three filterable views:

1. **Per-agent heat-map** — 10 KCs × 8 model systems of Yes / Equivocal / No /
   Protective calls for the selected agent, plus the paper-aggregate Strong /
   Moderate / Weak chip per KC.
2. **Per-KCC roster** — agents that received a positive (or other) call for a
   chosen KC, with volume coverage.
3. **Source ladder** — links straight to the Rusyn 2024 PDF stored locally.

The whole page degrades to a static notice in MOCKUP mode so it stays
deployable without a database.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.data_client import (
    DataSource,
    get_data_source,
    get_monograph_agent_matrix,
    list_agents,
    list_kccs,
    list_monograph_kcc_agents,
    list_monograph_volumes,
)
from app.page_shell import init_page

init_page("iarc_matrix")

st.markdown('<p class="mono">Analyze · IARC Monograph matrix</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display" style="font-size:2rem">IARC 10-year KCC retrospective</h1>',
    unsafe_allow_html=True,
)
st.caption(
    "Per-(agent, KC, model system) Yes / No / Equivocal / Protective calls extracted "
    "verbatim from IARC Monograph Volumes 112–130. Source: "
    "Rusyn et al. (2024), Toxicological Sciences 198(1):141-154 "
    "[doi:10.1093/toxsci/kfad134](https://doi.org/10.1093/toxsci/kfad134)."
)

if get_data_source() is DataSource.MOCKUP:
    st.info(
        "The IARC Monograph matrix is only available with a backing database. "
        "Run `alembic upgrade head` and then "
        "`python -m pipelines.import_10yr_kcc` to ingest the Rusyn 2024 data, "
        "or set `API_BASE_URL` to point at a running hKCC API."
    )
    st.stop()

volumes = list_monograph_volumes()
if not volumes:
    st.warning(
        "No IARC Monograph rows ingested yet. "
        "Run `python -m pipelines.import_10yr_kcc` to populate "
        "`iarc_monograph_kc_calls` and `iarc_monograph_kc_strength`."
    )
    st.stop()

with st.container(border=True):
    cols = st.columns(3)
    cols[0].metric("Volumes covered", len(volumes))
    cols[1].metric("Agents (paper)", len({v["volume"] for v in volumes}))
    cols[2].metric("Span", f"{volumes[0]['year']}–{volumes[-1]['year']}")
    st.caption(
        "Each Monograph volume contributes a Yes/No/Equivocal cell per "
        "(model system × KC) for every agent it covers."
    )

tab_agent, tab_kc, tab_refs = st.tabs(
    ["By agent", "By KC", "Source publication"]
)

# ── Tab 1: per-agent heat-map ───────────────────────────────────────────────
with tab_agent:
    agents = list_agents() or []
    monograph_agents = sorted(
        [a for a in agents if (a.get("source_ref_id") or "").startswith("rusyn2024")
         or a.get("name") in {
             # Curator-added agents that ARE in the Rusyn 2024 matrix
             "Benzene", "Glyphosate", "DDT", "Lindane", "Welding", "Pentachlorophenol",
             "Hydrazine", "Acrolein", "Styrene", "Diazinon", "Malathion",
         }],
        key=lambda a: (a.get("name") or "").lower(),
    )
    # Always allow searching all agents in case the paper-stub source tag wasn't set
    # on imports done from a pre-existing curator DB.
    if not monograph_agents:
        monograph_agents = sorted(agents, key=lambda a: (a.get("name") or "").lower())

    agent_choices = {f"{a['name']}  ·  {a.get('iarc_group') or '—'}": a["id"] for a in monograph_agents}
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
            st.caption(
                f"Covered in Monograph Vol(s): "
                f"{', '.join(matrix.get('monograph_volumes', []))}."
            )

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
        "_Toxicological Sciences_ 198(1):141–154.  \n"
        "DOI: [`10.1093/toxsci/kfad134`](https://doi.org/10.1093/toxsci/kfad134)"
    )
    local_pdf = Path("references/kcc-10yr/KCC-10yr.pdf")
    if local_pdf.is_file():
        st.caption(f"Local copy: `{local_pdf}`")
        try:
            data = local_pdf.read_bytes()
            st.download_button(
                "Download paper PDF",
                data=data,
                file_name=local_pdf.name,
                mime="application/pdf",
            )
        except OSError:
            st.caption("Could not read the local PDF copy.")
    st.markdown(
        "See `docs/KCC_EVIDENCE_RULES.md` for the deterministic algorithm that "
        "maps the paper's call cells to `evidence.score` in this database."
    )
