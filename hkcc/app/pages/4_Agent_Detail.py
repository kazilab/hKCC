"""Agent profile."""

import html

import streamlit as st

from hkcc.app.components.radar import render_radar
from hkcc.app.components.ref_card import render_ref_cards
from hkcc.app.data_client import (
    agent_evidence_map,
    evidence_for_agent,
    get_agent,
    get_monograph_agent_matrix,
    iarc_group_conflicts,
    list_kccs,
    references_for_agent,
)
from hkcc.app.page_shell import init_page
from hkcc.app.theme import EV_COLORS
from hkcc.app.utils.evidence import count_at_least, kcc_coverage
from hkcc.db.config import COMBINED_EXPOSURES, DERIVATION_REF_IDS
from hkcc.db.evidence_rules import LABEL_OFFSET_SHORT

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
dir_map = {e["kcc_id"]: e.get("direction", "positive") for e in evidence_rows}
kcad_refs = references_for_agent(agent_id)
cov = kcc_coverage(ev_map)
substantial = count_at_least(ev_map, 3)
convincing = count_at_least(ev_map, 4)
n_refs = sum(e["n_refs"] for e in evidence_rows)

# Per-(KCC, model system) calls behind the 10-year track's scores. A score of 0
# or a protective direction is only interpretable next to these: "Protective x1
# (primary)" in the notes is a summary, this is the evidence it summarises.
# Volume 100 agents have no rows here — that track derives from a figure, not a
# call table — so the breakdown is simply omitted for them.
_monograph = get_monograph_agent_matrix(agent_id) or {}
monograph_calls = _monograph.get("calls") or {}
# Documented in KCC_EVIDENCE_RULES.md as the systems Track B counts.
PRIMARY_SYSTEMS = ("Exposed Humans", "Human cells in vitro", "Mammalian in vivo")
CALL_MARK = {"Yes": "●", "Equivocal": "◐", "No": "○", "Protective": "↓"}

if st.button("← All agents"):
    st.switch_page("app/pages/3_Carcinogens.py")

caption_parts = [agent.get("iarc_group", "—") or "—", agent["agent_type"]]
if agent.get("cas") not in (None, "—"):
    caption_parts.append(f"CAS {agent['cas']}")
if agent.get("monograph_volume"):
    caption_parts.append(f"Monograph Vol. {agent['monograph_volume']}")
if agent.get("evaluation_year"):
    caption_parts.append(f"Evaluated {agent['evaluation_year']}")
_tracks = {"10yr-iarc": "10-yr retrospective (Rusyn 2024)", "vol100-kc": "Volume 100 re-review (Krewski 2019)"}
_agent_track = next((e.get("source_track") for e in evidence_rows if e.get("source_track")), None)
if _agent_track:
    caption_parts.append(f"Evidence source: {_tracks.get(_agent_track, _agent_track)}")
st.caption(" · ".join(str(p) for p in caption_parts if p))
st.markdown(f'<h1 class="h-display">{html.escape(str(agent["name"]))}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="lede">{html.escape(str(agent["summary"]))}</p>', unsafe_allow_html=True)

# `agent_sites` holds no rows in the shipped dataset, so a "Tumour sites" metric
# reads "—" for every agent — advertising a field the database cannot answer.
# It appears only when the agent actually has sites, as the tab already did.
_sites = agent.get("sites") or []

_metrics: list[tuple[str, object, str | None]] = [
    ("KCC coverage (ev ≥ 2)", f"{cov}/{len(kccs)}" if ev_map else "not scored", None),
    (
        "Substantial or better",
        f"{substantial}/{len(kccs)}" if ev_map else "—",
        "Characteristics scoring 3 or 4. Scores are ordinal, so they are counted, not summed.",
    ),
]
if _sites:
    _metrics.append(("Tumour sites", len(_sites), None))
_metrics += [
    ("Linked references", n_refs or "—", None),
    (
        "KCAD references",
        len(kcad_refs) or "—",
        "Assay annotations from the KCAD library. Literature coverage, not scored KCC evidence.",
    ),
]
for _col, (_label, _value, _help) in zip(st.columns(len(_metrics)), _metrics, strict=True):
    _col.metric(_label, _value, help=_help)

if ev_map:
    st.caption(LABEL_OFFSET_SHORT)

# An agent can carry dense KCAD literature and no scores at all — aniline has 96
# annotations and an entirely blank fingerprint. Without saying so, the empty
# profile reads as "investigated and found negative" rather than "outside the
# two IARC sources that produce scores".
if not ev_map:
    if kcad_refs:
        st.info(
            f"**No scored KCC evidence for this agent.** Its {len(kcad_refs)} KCAD "
            "reference(s) are assay literature mapped by Rigutto et al. 2025 — "
            "**KCAD contributes no evidence scores.** Scores come only from the IARC "
            "10-year retrospective and the Volume 100 re-review, neither of which "
            "covers this agent, so every characteristic below is *not assessed* "
            "rather than negative."
        )
    else:
        st.info(
            "**No scored KCC evidence for this agent.** Every characteristic below is "
            "*not assessed* rather than negative."
        )

# The database holds two IARC groups for three agents: the `agents` row and the
# group Rusyn et al. recorded alongside each strength label. Which is correct is
# a curation decision, so the disagreement is shown rather than silently picked.
_conflict = iarc_group_conflicts().get(agent_id)
if _conflict:
    st.warning(
        f"**Conflicting IARC classification.** This agent is recorded as "
        f"**Group {_conflict['agent_row']}** here, but the source strength table "
        f"(Rusyn et al. 2024) records **Group {', '.join(_conflict['source_table'])}** for "
        "the same substance. Check the IARC monograph for this agent before citing either "
        "value; hKCC does not adjudicate between them."
    )

# Combined evaluation units. IARC classified the components separately, so a
# single group on the merged row is not what IARC concluded.
if agent_id in COMBINED_EXPOSURES:
    st.warning(f"**Combined exposure.** {COMBINED_EXPOSURES[agent_id]}")

# The only agent without an IARC group is a KCAD umbrella label covering several
# isomers, which is not a unit IARC evaluates. Stated rather than left as a "—".
if not (agent.get("iarc_group") or "").strip("—").strip():
    st.warning(
        "**Not an IARC evaluation unit.** This entry has no IARC group because it is a "
        "generic KCAD label rather than a specific agent IARC assessed. See the summary "
        "above for the specific compound(s) that were evaluated."
    )

_tab_labels = ["KCC fingerprint", "Detailed evidence"]
if _sites:
    _tab_labels.append("Tumour sites")
_tab_labels += ["All references", "KCAD references"]
tab = st.tabs(_tab_labels)
_idx = {label: i for i, label in enumerate(_tab_labels)}

with tab[_idx["KCC fingerprint"]]:
    left, right = st.columns(2)
    with left:
        st.markdown("**Evidence profile**")
        st.caption(
            "One sector per characteristic, filled to its score. Characteristics that were "
            "never assessed are left empty behind a dashed spoke — not drawn as 0."
        )
        render_radar(kccs, ev_map, dir_map)
    with right:
        st.markdown(f"**All {len(kccs)} KCCs**")
        for k in kccs:
            v = ev_map.get(k["id"])
            if dir_map.get(k["id"]) == "protective":
                bar = (
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;'
                    f'color:{THEME["teal"]}">&#8595; protective</span>'
                )
            elif v is None:
                # Not evaluated for this agent — say so rather than drawing an
                # empty bar, which reads as "assessed and found negative".
                bar = (
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;'
                    f'color:{THEME["muted"]}">not assessed</span>'
                )
            else:
                bar = "".join(
                    f'<span style="display:inline-block;width:18px;height:8px;'
                    f"background:{EV_COLORS.get(i, EV_COLORS[0])};"
                    f'opacity:{1 if i <= v else 0.2};margin-right:2px;border-radius:1px"></span>'
                    for i in range(4)
                )
            st.markdown(
                f'<div style="display:grid;grid-template-columns:40px 1fr 120px;gap:8px;align-items:center;'
                f'padding:8px 0;border-bottom:1px solid {THEME["rule"]}">'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:10px">{k["n"]:02d}</span>'
                f"<span>{html.escape(str(k['short']))}</span>{bar}</div>",
                unsafe_allow_html=True,
            )

with tab[_idx["Detailed evidence"]]:
    st.caption(
        "Every assessed characteristic is listed, including those scoring 0 — a 0 is an "
        "assessment, not an absence of one. Characteristics with no row at all are shown as "
        '"not assessed" in the fingerprint above.'
    )
    _TRACK_LABEL = {
        "10yr-iarc": "10-yr retrospective (Rusyn et al. 2024)",
        "vol100-kc": "Volume 100 re-review (Krewski et al. 2019)",
    }
    for cell in sorted(evidence_rows, key=lambda c: c["kcc_id"]):
        k = kcc_by_id.get(cell["kcc_id"])
        if not k:
            continue
        direction = cell.get("direction", "positive")
        label = f"KCC-{k['n']:02d}: {k['title']} · score {cell['score']}/4"
        if direction != "positive":
            label += f" · {direction}"
        with st.expander(label, expanded=False):
            if direction == "protective":
                st.warning(
                    "The source reports this agent as **suppressing** this characteristic. "
                    "No positive evidence is recorded."
                )
            elif cell["score"] == 0:
                st.info(
                    "Assessed, but no positive evidence was reported in the primary model "
                    "systems. This is a finding, not a gap."
                )
            elif direction in ("equivocal", "negative", "unspecified"):
                st.caption(f"Direction: {direction} — read the score with the derivation below.")
            st.progress(cell["score"] / 4.0)

            # The methodology states a score is not self-interpreting, so the
            # derivation travels with it rather than living only in the export.
            meta = []
            track = cell.get("source_track")
            if track:
                meta.append(f"**Source.** {_TRACK_LABEL.get(track, track)}")
            if cell.get("source_count") is not None:
                denom = 3 if track == "10yr-iarc" else 4
                unit = "primary model systems" if track == "10yr-iarc" else "information sources"
                meta.append(f"**Count.** {cell['source_count']} of {denom} {unit}")
            if cell.get("data_role"):
                role = cell["data_role"]
                note = (
                    " — the IARC working group did **not** use this data in its evaluation"
                    if role == "Not used"
                    else ""
                )
                meta.append(f"**IARC data role.** {role}{note}")
            if meta:
                st.markdown("  \n".join(meta))
            if cell.get("curator_notes"):
                st.caption(f"Derivation: {cell['curator_notes']}")

            # Call-level breakdown. Without it a protective or 0-scoring cell
            # gives the reader no way to see *what* was reported, only that the
            # score came out low.
            cell_calls = {
                system: call
                for system, call in (monograph_calls.get(cell["kcc_id"]) or {}).items()
                if system != "Overall strength"
            }
            if cell_calls:
                st.markdown("**Model-system calls**")
                # `direction` records the dominant reading, so a pair whose
                # primary systems disagree (e.g. Yes in human cells, Protective
                # in mammalian in vivo) still reads "positive". Say so here,
                # where the conflicting calls are visible side by side.
                _primary_calls = {cell_calls[s] for s in PRIMARY_SYSTEMS if s in cell_calls} & {
                    "Yes",
                    "No",
                    "Protective",
                }
                if len(_primary_calls) > 1:
                    st.warning(
                        "**The primary systems disagree** ("
                        + ", ".join(sorted(_primary_calls))
                        + "). A single *Yes* is enough to record positive evidence, so the "
                        "cell's `direction` reflects the dominant reading, not the mixture. "
                        "Read the per-system calls below rather than the direction alone."
                    )
                ordered = [s for s in PRIMARY_SYSTEMS if s in cell_calls]
                ordered += [s for s in sorted(cell_calls) if s not in PRIMARY_SYSTEMS]
                st.dataframe(
                    [
                        {
                            "Model system": system,
                            "Counts toward score": "yes" if system in PRIMARY_SYSTEMS else "—",
                            "Call": f"{CALL_MARK.get(cell_calls[system], '')} {cell_calls[system]}",
                        }
                        for system in ordered
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(
                    "Only the three primary systems feed the score; the rest are supplementary "
                    "and are recorded but not counted."
                )
                if st.button(
                    "Open the full call matrix for this agent →",
                    key=f"iarc_link_{cell['kcc_id']}",
                ):
                    st.query_params["iarc_agent"] = agent_id
                    st.switch_page("app/pages/9b_IARC_Matrix.py")

            st.write(k["mechanism"])
            # "Anchored to N references" read as N primary mechanistic studies.
            # For 775 of 844 cells the only citation is the analysis the score
            # was derived from (Rusyn 2024 / Krewski 2019), not the underlying
            # experiments — so the derivation source and any additional
            # literature are now named for what they are.
            _refs = cell.get("refs", [])
            _derivation = [r for r in _refs if r["id"] in DERIVATION_REF_IDS]
            _supporting = [r for r in _refs if r["id"] not in DERIVATION_REF_IDS]
            if _derivation:
                st.caption(
                    "**Derivation source** — the published analysis this score was computed "
                    "from, not the underlying experiments."
                )
            if _supporting:
                st.caption(
                    f"**Supporting literature** — {len(_supporting)} study record(s) linked via the KCAD assay library."
                )
            for ref in _derivation + _supporting:
                st.markdown(f"**{ref.get('year', '—')}** · {ref['title']}")
                st.caption(f"{ref['authors']} · _{ref['journal']}_")
                if ref.get("doi") and ref["doi"] != "—":
                    doi = ref["doi"].replace("https://doi.org/", "")
                    st.markdown(
                        f'<a href="https://doi.org/{html.escape(doi)}" target="_blank" '
                        f'rel="noopener noreferrer">DOI</a>',
                        unsafe_allow_html=True,
                    )

if _sites:
    with tab[_idx["Tumour sites"]]:
        for site in _sites:
            with st.container(border=True):
                st.markdown(f"**{site}**")
                st.caption("Sufficient evidence in humans (IARC monograph)")

with tab[_idx["All references"]]:
    seen: set[str] = set()
    for cell in evidence_rows:
        for ref in cell.get("refs", []):
            if ref["id"] in seen:
                continue
            seen.add(ref["id"])
            st.markdown(f"**{ref.get('year', '—')}** · {ref['title']}")
            st.caption(f"{ref['authors']} · _{ref['journal']}_")

with tab[_idx["KCAD references"]]:
    if not kcad_refs:
        st.caption("No KCAD references are linked to this agent.")
    else:
        st.caption(
            f"{len(kcad_refs)} references imported from KCAD (Rigutto et al. 2025) "
            "via `monograph_chem → agent` mapping. Scores remain curator-driven; these are added literature."
        )
        PAGE_SIZE = 30
        if len(kcad_refs) > PAGE_SIZE:
            n_pages = (len(kcad_refs) - 1) // PAGE_SIZE + 1
            page = st.number_input("Page", min_value=1, max_value=n_pages, value=1, step=1, key="kcad_ref_page")
            start = (page - 1) * PAGE_SIZE
            rows = kcad_refs[start : start + PAGE_SIZE]
        else:
            rows = kcad_refs
        render_ref_cards(rows)
