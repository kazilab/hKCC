"""Methodology — how scores are derived, plus the KCAD assay source and dictionary.

This page documented the KCAD assay library only. The score derivation rules —
the actual scientific product — lived solely in ``docs/KCC_EVIDENCE_RULES.md``,
which ships in neither the wheel nor the Streamlit deployment, so a reader could
compare agents by score without ever encountering the rules that produced them
or the caveats attached to them.
"""

from __future__ import annotations

import html

import streamlit as st

from hkcc.app.components.card import card
from hkcc.app.data_client import (
    get_evidence_rules,
    get_source_paper,
    list_abbreviations,
    list_column_definitions,
)
from hkcc.app.page_shell import init_page

RULES_DOC = "https://github.com/kazilab/hkcc/blob/main/docs/KCC_EVIDENCE_RULES.md"

init_page("methodology")

paper = get_source_paper() or {}

st.markdown('<p class="mono">Methodology</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display" style="font-size:2rem">How hKCC derives its scores</h1>',
    unsafe_allow_html=True,
)

tab_scores, tab_kcad = st.tabs(["Evidence scoring", "KCAD source & dictionary"])

with tab_scores:
    rules = get_evidence_rules()
    if not rules:
        st.info("Scoring rules need a backing database or API.")
    else:
        stats = rules["stats"]
        by_track = stats["by_track"]
        n_ten = by_track.get("10yr-iarc", 0)
        n_v100 = by_track.get("vol100-kc", 0)

        st.caption(
            f"Every one of the {stats['total_cells']} scores in this database was computed "
            "from a published source table by a deterministic rule. No score was assigned "
            "by hand. The rules differ by source, so the same number does not mean the "
            "same thing across tracks."
        )
        st.info(
            "**Coverage gap: IARC Monograph Volumes 107–111.** The two scoring sources are the "
            "Volume 100 Group 1 re-review and Volumes 112–130. Nothing covers Volumes 107–111, "
            "so an agent evaluated only in that window has no scored evidence here — that is a "
            "gap in coverage, not a finding about the agent."
        )

        st.markdown("#### The scale")
        st.dataframe(
            [{"Score": row["score"], "Tier": row["label"], "Meaning": row["meaning"]} for row in rules["score_scale"]],
            hide_index=True,
            use_container_width=True,
        )
        st.warning(
            "**The scale is ordinal.** A 4 is not twice a 2, and the derivations give no "
            "basis for adding scores. Count how many characteristics clear a threshold; "
            "do not sum them."
        )
        st.caption(
            "The tier names avoid *Strong*, *Moderate* and *Weak* on purpose — those are "
            "the verbatim Rusyn et al. 2024 labels and mean something different here."
        )

        st.markdown(f"#### Track A — standardized strength labels · {stats['track_a_rows']} cells")
        st.caption("Used whenever Rusyn et al. 2024 published a strength label for the pair; Track B is the fallback.")
        st.dataframe(
            [
                {
                    "Source label": label,
                    "hKCC score": score,
                    "Cells": stats["track_a_labels"].get(label, 0),
                }
                for label, score in rules["track_a_map"].items()
            ],
            hide_index=True,
            use_container_width=True,
        )
        if stats.get("label_overridden_by_direction"):
            st.caption(
                f"*Cells* counts labels, not scores: {stats['label_overridden_by_direction']} of "
                "these cells score 0 regardless of their label, because the primary systems "
                "report the agent as protective. Direction overrides the mapping."
            )
        st.warning(rules["caveats"]["label_offset"])

        st.markdown("**How the IARC working group actually used the data**")
        st.dataframe(
            [
                {
                    "data_role": role,
                    "Meaning": meaning,
                    "Cells": stats["data_roles"].get(role, 0),
                }
                for role, meaning in rules["data_role_meaning"].items()
            ],
            hide_index=True,
            use_container_width=True,
        )
        n_not_used = stats["data_roles"].get("Not used", 0)
        n_not_used_pos = stats.get("not_used_score_ge_2", n_not_used)
        n_not_used_zero = stats.get("not_used_score_0", 0)
        st.warning(
            f"{rules['caveats']['data_role']}\n\n"
            f"**{n_not_used} of the {stats['track_a_rows']} Track A cells "
            f"({stats['not_used_share']}%) are marked *Not used*.** "
            f"**{n_not_used_pos}** of those still score 2–4; "
            f"**{n_not_used_zero}** score 0 because direction is protective and overrides the label."
        )
        if stats.get("label_outruns_primary"):
            st.info(
                f"{rules['caveats'].get('label_outruns_primary', '')}\n\n"
                f"**{stats['label_outruns_primary']} Track A cells** currently score ≥2 while "
                f"primary systems alone would not support a positive call "
                f"({stats.get('label_outruns_by_direction', {})})."
            )

        st.markdown(f"#### Track B — model-system call counts · {stats['track_b_rows']} cells")
        st.caption(
            "Used where the paper published no strength label. The score counts how many "
            "of the three primary model systems reported a positive call: "
            + ", ".join(rules["primary_systems"])
            + ". Calls in other systems are recorded but do not count."
        )
        st.dataframe(
            [{"Primary systems positive": count, "hKCC score": score} for count, score in rules["track_b_map"].items()],
            hide_index=True,
            use_container_width=True,
        )
        st.warning(rules["caveats"]["track_b_attribution"])

        st.markdown(f"#### Volume 100 re-review · {n_v100} cells")
        st.caption(
            "Krewski et al. 2019, Figure 22.4. Colour intensity encodes how many of four "
            "information source types reported the characteristic, so the score is a count "
            "of source types — not a strength judgement."
        )
        st.dataframe(
            [
                {
                    "Figure colour": row["colour"],
                    "Source types": row["sources"],
                    # Kept as text: "White" writes no cell at all, and mixing an
                    # int with that string makes the column unrenderable.
                    "hKCC score": "no cell written" if row["score"] is None else str(row["score"]),
                }
                for row in rules["vol100_map"]
            ],
            hide_index=True,
            use_container_width=True,
        )
        st.warning(
            rules["caveats"]["within_track_mixing"]
            + f"\n\n**{stats['agents_mixing_derivations']} of the {stats['ten_year_agents']} "
            "10-year agents** carry both derivations."
        )
        st.info(
            f"**Do not compare across tracks.** {n_ten} cells come from the 10-year "
            f"retrospective and {n_v100} from the Volume 100 re-review. A 3 derived from a "
            "*Moderate* label and a 3 derived from two shaded source types are not "
            "equivalent measurements."
        )

        st.markdown("#### Zero, protective, and not assessed")
        st.caption(
            f"{stats['zero_cells']} cells score 0 — a finding, not a gap: the pair was "
            "assessed and no positive evidence was reported in the primary systems. "
            f"{stats['protective_cells']} cells are marked *protective*, meaning the source "
            "reports the agent as suppressing that characteristic; these are never placed "
            "on the positive scale. A pair that was never assessed has no cell at all — it "
            "is omitted from the API, left blank in exports, and shown as *not assessed*."
        )

        st.markdown(
            f"Full derivation, including precedence between tracks and how to verify these "
            f"rules against the shipped data: "
            f'<a href="{RULES_DOC}" target="_blank" rel="noopener noreferrer">'
            "KCC_EVIDENCE_RULES.md</a>.",
            unsafe_allow_html=True,
        )

with tab_kcad:
    st.caption(
        "Every assay, annotation and KCAD-derived agent in hKCC is anchored to the "
        "publication below. Browse the column dictionary and abbreviation glossary "
        "to understand how the data was originally encoded. **KCAD contributes no "
        "evidence scores** — it supplies the assay library only."
    )

    # ── Source paper card ────────────────────────────────────────────────────────
    with card("methodology-source"):
        st.markdown("### Source publication")
        if paper:
            title = paper.get("title", "—")
            authors = paper.get("authors", "—")
            journal = paper.get("journal", "—")
            year = paper.get("year", "—")
            vol = paper.get("vol")
            article_id = paper.get("article_id")
            doi = paper.get("doi")
            url = paper.get("url") or (f"https://doi.org/{doi}" if doi else None)

            st.markdown(f"**{title}**")
            st.caption(
                f"{authors} · _{journal}_ ({year})"
                + (f", vol. {vol}" if vol else "")
                + (f", article {article_id}" if article_id else "")
            )
            if doi:
                st.markdown(
                    "DOI: "
                    f'<a href="{html.escape(url or "")}" target="_blank" rel="noopener noreferrer">'
                    f"<code>{html.escape(doi)}</code></a>"
                    " · Database URL: "
                    '<a href="https://kcad.cchem.berkeley.edu" target="_blank" rel="noopener noreferrer">'
                    "<code>https://kcad.cchem.berkeley.edu</code></a>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Paper reference row not found in this database.")

    # ── Abbreviations ───────────────────────────────────────────────────────────
    abbrevs = list_abbreviations()
    st.markdown(f"### Abbreviations ({len(abbrevs)})")
    st.caption(
        "Sourced from Supplementary Table 3 of the KCAD paper. Used throughout the assay endpoints, "
        "biomarkers and notes."
    )
    if not abbrevs:
        st.caption("No abbreviations found in this database.")
    else:
        q = st.text_input(
            "Search abbreviations",
            placeholder="e.g. 8-OHdG, ROS, BAX",
            key="abbrev_search",
        )
        filtered = abbrevs
        if q:
            ql = q.lower()
            filtered = [a for a in abbrevs if ql in a["abbreviation"].lower() or ql in a["expansion"].lower()]
        st.caption(f"Showing {len(filtered)} / {len(abbrevs)}")
        cols = st.columns(2)
        for i, a in enumerate(filtered):
            with cols[i % 2]:
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px dotted #ccc">'
                    f"<code>{a['abbreviation']}</code> &nbsp;→&nbsp; {a['expansion']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Column dictionary ───────────────────────────────────────────────────────
    defs = list_column_definitions()
    st.markdown(f"### Column dictionary ({len(defs)})")
    st.caption(
        "Definitions for every column of the KCAD annotation table "
        "(Supplementary Table 2). These are surfaced as tooltips on the Assays "
        "page detail view."
    )
    if not defs:
        st.caption("No column definitions found in this database.")
    else:
        for d in defs:
            flag = " ⚠" if d.get("hkcc_note") else ""
            with st.expander(f"`{d['column_name']}`{flag}"):
                st.write(d["definition"])
                st.caption("Definition quoted verbatim from Supplementary Table 2.")
                if d.get("hkcc_note"):
                    # The published text does not describe this column. Both are
                    # shown: the source stays quotable, the reader stays correct.
                    st.warning(f"**What this column holds in hKCC.** {d['hkcc_note']}")
