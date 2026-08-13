"""The derivation rules behind ``evidence.score``, as data.

``docs/KCC_EVIDENCE_RULES.md`` is the prose reference, but it does not ship in
the wheel and a Streamlit Cloud user has no repo checkout — so pointing readers
at a Markdown path left the rules effectively unpublished. The scoring rules are
the scientific product; someone reading a 4 in the matrix needs to know it may
have come from a source label the IARC working group explicitly did not use.

This module is the in-app source of truth. The mappings are stated once here and
the counts are computed from the database at call time, so the Methodology page
cannot quote a figure the data does not support.
``tests/test_methodology_rules.py`` asserts both against the shipped rows.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from hkcc.db.models import Evidence, IarcMonographKcStrength

# hkcc score -> (tier name, meaning). Deliberately not "Strong/Moderate/Weak":
# those are the verbatim Rusyn et al. 2024 labels and mean something different
# here -- an hKCC 3 comes from a source label of *Moderate*.
SCORE_SCALE: list[tuple[int, str, str]] = [
    (0, "None", "No positive evidence in the primary model systems"),
    (1, "Equivocal", "Mixed / inconclusive, no convergent yes"),
    (2, "Limited", "Weakest positive tier (see per-track derivation)"),
    (3, "Substantial", "Middle positive tier"),
    (4, "Convincing", "Strongest positive tier"),
]

# Track A: the standardized strength label the paper published for the pair.
TRACK_A_MAP: dict[str, int] = {"Strong": 4, "Moderate": 3, "Weak": 2}

# Track B: how many of the three primary model systems reported a positive call.
# These calls are Rusyn & Wright's retrospective coding of monograph content, not
# IARC Working Group determinations -- only the Track A strength label and data
# role are extracted Working Group outputs. Stated wherever Track B is shown.
PRIMARY_SYSTEMS: tuple[str, ...] = ("Exposed Humans", "Human cells in vitro", "Mammalian in vivo")
TRACK_B_MAP: dict[int, int] = {1: 2, 2: 3, 3: 4}

# Volume 100: how many of the four information source types Figure 22.4 shades.
VOL100_MAP: list[tuple[str, str, int | None]] = [
    ("Red", "4", 4),
    ("Orange", "3", 4),
    ("Yellow", "2", 3),
    ("Green", "1", 2),
    ("White", "none", None),
]

# Filtering to one source is not enough to make profiles comparable: most 10-yr
# agents carry a mix of Track A (label-derived) and Track B (count-derived)
# cells, so a single agent's own profile spans two measurements.
WITHIN_TRACK_MIXING_CAVEAT = (
    "**Filtering by source does not make a profile internally comparable.** Within the "
    "10-year retrospective, most agents carry both label-derived (Track A) and count-derived "
    "(Track B) cells, so two characteristics of the *same* agent can hold the same number "
    "from different measurements. Read each cell's derivation, not the shape of the profile."
)

TRACK_B_ATTRIBUTION = (
    "**Track B rests on author coding, not Working Group determinations.** The per-model-system "
    "Yes / No / Equivocal / Protective calls were made by Rusyn and Wright when they coded the "
    "monographs into a comparable cross-volume matrix. Only the standardized strength label and "
    "data role (Track A) are extracted IARC Working Group outputs. Do not cite a Track B score "
    "as an IARC Working Group finding."
)

DATA_ROLE_MEANING: dict[str, str] = {
    "Not used": "The working group did not use this data in its evaluation",
    "Supportive": "Used as supporting evidence",
    "Upgrade": "Used to upgrade the overall classification",
}

LABEL_OFFSET_CAVEAT = (
    "**The mapping shifts every source label one rung up.** A pair the paper called "
    "*Weak* scores 2, *Moderate* scores 3, *Strong* scores 4. The scale has no score "
    'reserved for "positive but weaker than the paper\'s weakest label". When checking '
    "hKCC against the source publication, compare the labels recorded in each cell's "
    "derivation note — not the numbers."
)

# The one-line form, for pages where the full caveat would crowd the content.
# Same fact, one source: the wording cannot diverge between pages.
LABEL_OFFSET_SHORT = (
    "Source labels map one rung up — *Weak* → 2, *Moderate* → 3, *Strong* → 4 — so an hKCC "
    "number is not the paper's label. Compare labels, not numbers."
)

DATA_ROLE_CAVEAT = (
    "**A high score does not mean IARC relied on the data.** The score reflects the "
    "published strength label alone, while `data_role` records how the working group "
    "actually used the mechanistic evidence. Almost every cell marked *Not used* still "
    "scores 2–4; the only exceptions are protective cells, where direction overrides "
    "the label and the score is 0. The role travels with every cell and is exposed at "
    "`GET /api/v1/monograph/strengths`."
)

# Track A can assign a positive score from a File014 label even when primary
# File012 systems report no Yes. Those cells are intentional residuals, not bugs:
# the label may synthesise evidence the call table does not tabulate. Direction
# records the primary-call picture so the tension is visible.
LABEL_OUTRUNS_PRIMARY_CAVEAT = (
    "**A File014 label can outrun the primary File012 calls.** Track A applies the "
    "published strength label even when no primary model system reported Yes — for "
    "example when primary calls are only No/Equivocal, or when no primary row was "
    "tabulated at all (`direction = unspecified`). The score stands, because the "
    "label may draw on supplementary systems File012 does not promote to the score; "
    "always read `direction` (and the derivation note) with the number."
)


def evidence_rules_payload(db: Session) -> dict:
    """The whole rule set, ready to serve or render.

    Built here rather than in the API router so the Streamlit app can call it
    directly on the database path and get byte-identical content to the API —
    the two serialisations of an agent drifted exactly this way once already.
    """
    return {
        "score_scale": [{"score": score, "label": label, "meaning": meaning} for score, label, meaning in SCORE_SCALE],
        "track_a_map": TRACK_A_MAP,
        "track_b_map": {str(count): score for count, score in TRACK_B_MAP.items()},
        "primary_systems": list(PRIMARY_SYSTEMS),
        "vol100_map": [{"colour": colour, "sources": sources, "score": score} for colour, sources, score in VOL100_MAP],
        "data_role_meaning": DATA_ROLE_MEANING,
        "caveats": {
            "label_offset": LABEL_OFFSET_CAVEAT,
            "data_role": DATA_ROLE_CAVEAT,
            "label_outruns_primary": LABEL_OUTRUNS_PRIMARY_CAVEAT,
            "track_b_attribution": TRACK_B_ATTRIBUTION,
            "within_track_mixing": WITHIN_TRACK_MIXING_CAVEAT,
        },
        "stats": evidence_rule_stats(db),
    }


def evidence_rule_stats(db: Session) -> dict:
    """Row counts behind each rule, computed from the shipped data."""
    strengths = {(s.agent_id, s.kcc_id): s for s in db.scalars(select(IarcMonographKcStrength))}
    evidence = list(db.scalars(select(Evidence)))
    ten_year = [e for e in evidence if e.source_track == "10yr-iarc"]
    track_a = [e for e in ten_year if (e.agent_id, e.kcc_id) in strengths]
    track_b = [e for e in ten_year if (e.agent_id, e.kcc_id) not in strengths]

    labels = Counter(strengths[(e.agent_id, e.kcc_id)].strength_label for e in track_a)
    roles = Counter(strengths[(e.agent_id, e.kcc_id)].data_role for e in track_a)
    # Protective cells keep their label but score 0, so label counts and score
    # counts are not the same number. Reported separately rather than conflated.
    scored_by_label = Counter((strengths[(e.agent_id, e.kcc_id)].strength_label, e.score) for e in track_a)
    overridden = [e for e in track_a if e.score != TRACK_A_MAP.get(strengths[(e.agent_id, e.kcc_id)].strength_label)]
    not_used_cells = [e for e in track_a if strengths[(e.agent_id, e.kcc_id)].data_role == "Not used"]
    # Positive Track A scores whose primary-call direction is not "positive":
    # the File014 label outran what primary File012 systems alone would support.
    outruns = [e for e in track_a if e.score >= 2 and e.direction in ("unspecified", "negative", "equivocal")]
    derivations_per_agent: defaultdict[str, set[str]] = defaultdict(set)
    for e in ten_year:
        derivations_per_agent[e.agent_id].add("A" if (e.agent_id, e.kcc_id) in strengths else "B")
    mixed_agents = [a for a, kinds in derivations_per_agent.items() if len(kinds) > 1]
    return {
        "total_cells": len(evidence),
        "by_track": dict(Counter(e.source_track for e in evidence)),
        "track_a_rows": len(track_a),
        "track_b_rows": len(track_b),
        "track_a_labels": dict(labels),
        "track_a_label_scores": {f"{label}:{score}": n for (label, score), n in scored_by_label.items()},
        "data_roles": dict(roles),
        # Cells whose label would map to 2-4 but which score 0 because the
        # primary systems report the agent as protective. Direction wins.
        "label_overridden_by_direction": len(overridden),
        # Agents whose own profile spans both derivations within one track.
        "ten_year_agents": len(derivations_per_agent),
        "agents_mixing_derivations": len(mixed_agents),
        # Of the Not used rows: how many still present as positive evidence.
        "not_used_score_ge_2": sum(1 for e in not_used_cells if e.score >= 2),
        "not_used_score_0": sum(1 for e in not_used_cells if e.score == 0),
        "not_used_share": round(100 * roles.get("Not used", 0) / max(len(track_a), 1)),
        "zero_cells": sum(1 for e in evidence if e.score == 0),
        "protective_cells": sum(1 for e in evidence if e.direction == "protective"),
        "label_outruns_primary": len(outruns),
        "label_outruns_by_direction": dict(Counter(e.direction for e in outruns)),
    }
