"""Verify the shipped scores against docs/KCC_EVIDENCE_RULES.md.

The methodology document used to contradict how the data was actually produced:
it stated that the File014 strength labels "do not feed evidence.score" when in
fact they were the primary track for half the matrix. The importer that made
these rows is no longer part of the distribution, so the document is the only
record — these tests keep it honest by recomputing every score from the
``iarc_monograph_*`` tables and asserting the documented rules reproduce the
shipped database exactly.

If a data update changes how scores are derived, these fail until the document
is updated to match.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest
from sqlalchemy import select

from hkcc.db.models import Evidence, IarcMonographKcCall, IarcMonographKcStrength
from hkcc.db.session import SessionLocal

# Documented in KCC_EVIDENCE_RULES.md → "Track A"
STRENGTH_TO_SCORE = {"Strong": 4, "Moderate": 3, "Weak": 2}
# Documented in KCC_EVIDENCE_RULES.md → "Track B"
PRIMARY_MODEL_SYSTEMS = ("Exposed Humans", "Human cells in vitro", "Mammalian in vivo")
OVERALL_STRENGTH = "Overall strength"


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def facts(db):
    strengths = {(s.agent_id, s.kcc_id): s for s in db.scalars(select(IarcMonographKcStrength))}
    # Counts **distinct model systems**, not call rows. Counting rows made the
    # score depend on how many volumes happened to report a pair: if a later
    # volume re-evaluates the same agent x system, a row count could exceed 3
    # without three distinct systems ever agreeing. There are no such duplicates
    # today (so every score is unchanged), but the rule is now stated in a form
    # that cannot break on the next import.
    #
    # A system counts as Yes if *any* volume reported Yes for it. That matches
    # how the API's per-agent heat map already resolves cross-volume conflicts
    # (Yes > Equivocal > No > Protective).
    primary = defaultdict(lambda: defaultdict(set))
    seen_any_call: set[tuple[str, str]] = set()
    for c in db.scalars(select(IarcMonographKcCall)):
        if c.model_system == OVERALL_STRENGTH:
            continue
        key = (c.agent_id, c.kcc_id)
        seen_any_call.add(key)
        if c.model_system in PRIMARY_MODEL_SYSTEMS:
            primary[key][c.call].add(c.model_system)
    # Only the 10-year retrospective track is governed by the rules below; the
    # Volume 100 track (prefix [vol100-kc]) has its own section in the document
    # and its own tests.
    evidence = [e for e in db.scalars(select(Evidence)) if (e.curator_notes or "").startswith("[10yr-iarc]")]
    return strengths, primary, seen_any_call, evidence


def _expected_score(key, strengths, primary) -> int | None:
    counts = primary.get(key, {})
    # Direction overrides strength. If the primary systems report the agent as
    # suppressing the characteristic and none reports a Yes, there is no
    # positive evidence to record, whatever the standardized label says.
    if counts.get("Protective") and not counts.get("Yes"):
        return 0
    if key in strengths:
        return STRENGTH_TO_SCORE.get(strengths[key].strength_label)
    yes = len(counts.get("Yes", ()))
    if yes >= 3:
        return 4
    if yes == 2:
        return 3
    if yes == 1:
        return 2
    if counts.get("Equivocal"):
        return 1
    return 0


def test_every_score_matches_the_documented_rules(facts):
    strengths, primary, seen_any_call, evidence = facts
    mismatches = []
    for e in evidence:
        key = (e.agent_id, e.kcc_id)
        if key not in strengths and key not in seen_any_call:
            mismatches.append((key, e.score, "no source rows"))
            continue
        expected = _expected_score(key, strengths, primary)
        if expected != e.score:
            mismatches.append((key, e.score, expected))
    assert not mismatches, f"{len(mismatches)} rows contradict the documented rules: {mismatches[:5]}"


def test_track_split_matches_the_document(facts):
    """250 rows via strength labels, 252 via call counts."""
    strengths, _, _, evidence = facts
    track_a = sum(1 for e in evidence if (e.agent_id, e.kcc_id) in strengths)
    assert len(evidence) == 502
    assert track_a == 250
    assert len(evidence) - track_a == 252


def test_strength_label_row_counts(db):
    """The label → score table in the document, by row count."""
    counts = defaultdict(int)
    for s in db.scalars(select(IarcMonographKcStrength)):
        counts[s.strength_label] += 1
    assert dict(counts) == {"Strong": 92, "Moderate": 95, "Weak": 63}


def test_data_role_counts_and_that_not_used_still_scores(db, facts):
    """147 'Not used' cells: 145 score 2-4, 2 score 0 (protective override)."""
    strengths, _, _, evidence = facts
    roles = defaultdict(int)
    for s in strengths.values():
        roles[s.data_role] += 1
    assert dict(roles) == {"Not used": 147, "Supportive": 65, "Upgrade": 38}

    scores = {e.agent_id + e.kcc_id: e.score for e in evidence}
    directions = {e.agent_id + e.kcc_id: e.direction for e in evidence}
    not_used = [scores[a + k] for (a, k), s in strengths.items() if s.data_role == "Not used" and (a + k) in scores]
    assert len(not_used) == 147
    # Track A yields 2-4 except where the primary calls report suppression, in
    # which case direction wins and the score is 0 (drinking coffee KC5/KC6).
    non_protective = [
        scores[a + k]
        for (a, k), s in strengths.items()
        if s.data_role == "Not used" and (a + k) in scores and directions.get(a + k) != "protective"
    ]
    assert min(non_protective) >= 2, "Track A yields 0 only for protective cells"
    assert sum(1 for v in not_used if v >= 2) == 145
    assert sum(1 for v in not_used if v < 2) == 2, "exactly the two protective cells score 0"


def test_supplementary_only_pairs_all_score_zero(facts):
    """144 cells score 0 while holding calls only in supplementary systems."""
    strengths, primary, seen_any_call, evidence = facts
    supp_only = [
        e.score
        for e in evidence
        if (e.agent_id, e.kcc_id) not in strengths
        and (e.agent_id, e.kcc_id) in seen_any_call
        and (e.agent_id, e.kcc_id) not in primary
    ]
    assert len(supp_only) == 144
    assert set(supp_only) == {0}


def test_supplementary_only_cells_split_into_positive_and_not(db, facts):
    """Only 32 of the 144 hold a positive call; 112 hold none.

    The document described all 144 as "evidence exists but only in supplementary
    model systems", and this test only asserted that *some* call existed — so a
    false statement about 112 cells passed. A score of 0 with no positive call
    anywhere is a different finding from one where a supplementary system said
    Yes, and the methodology now names them separately.
    """
    strengths, primary, seen_any_call, evidence = facts
    by_pair = defaultdict(set)
    for c in db.scalars(select(IarcMonographKcCall)):
        if c.model_system != OVERALL_STRENGTH:
            by_pair[(c.agent_id, c.kcc_id)].add(c.call)

    supp_only = [
        (e.agent_id, e.kcc_id)
        for e in evidence
        if (e.agent_id, e.kcc_id) not in strengths
        and (e.agent_id, e.kcc_id) in seen_any_call
        and (e.agent_id, e.kcc_id) not in primary
    ]
    with_positive = [k for k in supp_only if "Yes" in by_pair[k]]
    without = [k for k in supp_only if "Yes" not in by_pair[k]]

    assert len(with_positive) == 32, "documented supplementary_positive count is stale"
    assert len(without) == 112, "documented not_scored_by_rule count is stale"
    # The no-positive group really holds nothing positive, in any system.
    assert all("Yes" not in by_pair[k] for k in without)
    assert {call for k in without for call in by_pair[k]} <= {"No", "Equivocal"}

    text = (Path(__file__).resolve().parents[1] / "docs" / "KCC_EVIDENCE_RULES.md").read_text(
        encoding="utf-8"
    )
    assert "supplementary_positive" in text and "not_scored_by_rule" in text
    assert "evidence exists but only in supplementary model systems (144 cells)" not in text.lower()


def test_every_row_carries_a_known_provenance_marker(db):
    """Precedence keys off the notes prefix; every row must declare a track."""
    known = ("[10yr-iarc]", "[vol100-kc]")
    unmarked = [
        (e.agent_id, e.kcc_id) for e in db.scalars(select(Evidence)) if not (e.curator_notes or "").startswith(known)
    ]
    assert not unmarked, f"evidence rows with no source tag: {unmarked[:5]}"


def test_volume_100_track_never_writes_a_zero(db):
    """White in Fig. 22.4 means "No Source" — absence of data, not a negative.

    Those cells are left without an evidence row so the matrix shows them as
    not assessed rather than asserting evidence of absence.
    """
    zeros = [
        (e.agent_id, e.kcc_id)
        for e in db.scalars(select(Evidence))
        if (e.curator_notes or "").startswith("[vol100-kc]") and e.score == 0
    ]
    assert not zeros, f"Volume 100 rows scored 0: {zeros[:5]}"


def test_volume_100_track_uses_the_documented_mapping(db):
    """1 source -> 2, 2 sources -> 3, 3-4 sources -> 4. Score 1 is unused."""
    scores = {e.score for e in db.scalars(select(Evidence)) if (e.curator_notes or "").startswith("[vol100-kc]")}
    assert scores <= {2, 3, 4}, f"unexpected Volume 100 scores: {sorted(scores)}"
    assert 1 not in scores, "score 1 is reserved for equivocal, which this source lacks"


# --- direction: strength and sign are separate axes --------------------------


def test_no_protective_cell_carries_positive_evidence(db):
    """Regression: drinking coffee x KC5 scored 2 while every primary system
    reported the agent as *suppressing* oxidative stress. A protective cell
    must never present as positive evidence of the characteristic."""
    offenders = [
        (e.agent_id, e.kcc_id, e.score)
        for e in db.scalars(select(Evidence))
        if e.direction == "protective" and e.score > 0
    ]
    assert not offenders, f"protective cells scored as positive evidence: {offenders}"


def test_the_two_tracks_agree_on_protective(db):
    """Track B always scored protective cells 0; Track A must now match."""
    by_track = {"A": [], "B": [], "vol100": []}
    for e in db.scalars(select(Evidence)):
        if e.direction != "protective":
            continue
        notes = e.curator_notes or ""
        track = "vol100" if notes.startswith("[vol100-kc]") else ("A" if "File014" in notes else "B")
        by_track[track].append(e.score)
    for track, scores in by_track.items():
        assert all(s == 0 for s in scores), f"track {track} scores a protective cell: {scores}"


def test_direction_uses_the_controlled_vocabulary(db):
    allowed = {"positive", "protective", "equivocal", "negative", "unspecified"}
    used = {e.direction for e in db.scalars(select(Evidence))}
    assert used <= allowed, f"unknown direction values: {used - allowed}"


def test_coffee_oxidative_stress_is_recorded_as_protective(db):
    """The exact cell the methodology document cites as protective."""
    e = db.scalar(select(Evidence).where(Evidence.agent_id == "drinking-coffee", Evidence.kcc_id == "kcc-05"))
    assert e is not None
    assert e.direction == "protective"
    assert e.score == 0
    assert "Weak" in (e.curator_notes or ""), "the File014 label must still be recorded"


def test_api_exposes_direction_with_the_score(client):
    """A consumer reading only `score` would misread a protective cell."""
    from hkcc.api.schemas import EvidenceCellOut, MatrixRowOut

    assert "direction" in EvidenceCellOut.model_fields
    assert "directions" in MatrixRowOut.model_fields


# --- the two tracks are not interchangeable ---------------------------------


def test_every_row_declares_its_source_track(db):
    tracks = {e.source_track for e in db.scalars(select(Evidence))}
    assert tracks <= {"10yr-iarc", "vol100-kc"}, f"unknown source_track values: {tracks}"


def test_source_track_agrees_with_the_curator_notes_prefix(db):
    """The field and the note prefix must not drift apart."""
    bad = [
        (e.agent_id, e.kcc_id, e.source_track)
        for e in db.scalars(select(Evidence))
        if e.source_track != ("vol100-kc" if (e.curator_notes or "").startswith("[vol100-kc]") else "10yr-iarc")
    ]
    assert not bad, f"source_track disagrees with curator_notes: {bad[:5]}"


def test_no_agent_mixes_the_two_tracks(db):
    """Mixing would make an agent's own coverage and weight incoherent."""
    from collections import defaultdict

    by_agent = defaultdict(set)
    for e in db.scalars(select(Evidence)):
        by_agent[e.agent_id].add(e.source_track)
    mixed = {a: t for a, t in by_agent.items() if len(t) > 1}
    assert not mixed, f"agents mixing evidence tracks: {mixed}"


def test_volume_100_source_counts_survived_the_score_mapping(db):
    """3 and 4 sources both map to score 4; source_count keeps them distinct."""
    rows = [e for e in db.scalars(select(Evidence)) if e.source_track == "vol100-kc"]
    assert rows, "no Volume 100 rows"
    assert all(e.source_count in (1, 2, 3, 4) for e in rows), "every Volume 100 row needs a count"
    at_4 = [e.source_count for e in rows if e.score == 4]
    assert set(at_4) == {3, 4}, f"score 4 should cover 3 and 4 sources, got {set(at_4)}"
    assert at_4.count(3) > 0 and at_4.count(4) > 0


def test_volume_100_never_uses_score_0_or_1(db):
    """The source has no negative or equivocal category; documented as such."""
    scores = {e.score for e in db.scalars(select(Evidence)) if e.source_track == "vol100-kc"}
    assert scores <= {2, 3, 4}, f"unexpected Volume 100 scores: {sorted(scores)}"


# --- provenance travels with the score --------------------------------------


def test_evidence_cell_api_carries_everything_needed_to_read_a_score():
    """The methodology says a score is not self-interpreting; the API must
    therefore ship the derivation with it, not only in the release export."""
    from hkcc.api.schemas import EvidenceCellOut

    required = {"score", "direction", "source_track", "source_count", "data_role", "curator_notes"}
    missing = required - set(EvidenceCellOut.model_fields)
    assert not missing, f"EvidenceCellOut omits interpretive fields: {missing}"


def test_track_a_rows_carry_the_iarc_data_role(db):
    """Track A cells carry data_role (most Not used still score 2-4; protective score 0)."""
    labelled = {(s.agent_id, s.kcc_id) for s in db.scalars(select(IarcMonographKcStrength))}
    missing = [
        (e.agent_id, e.kcc_id)
        for e in db.scalars(select(Evidence))
        if (e.agent_id, e.kcc_id) in labelled and not e.data_role
    ]
    assert not missing, f"label-track rows without a data_role: {missing[:5]}"


def test_data_role_is_absent_where_the_source_supplies_none(db):
    """Only the 10-yr label track has a data role; Volume 100 has no equivalent."""
    stray = [
        (e.agent_id, e.kcc_id, e.data_role)
        for e in db.scalars(select(Evidence))
        if e.source_track == "vol100-kc" and e.data_role
    ]
    assert not stray, f"Volume 100 rows claiming an IARC data role: {stray[:5]}"


def test_every_row_has_a_derivation_note(db):
    """curator_notes is the human-readable derivation and must never be blank."""
    blank = [(e.agent_id, e.kcc_id) for e in db.scalars(select(Evidence)) if not (e.curator_notes or "").strip()]
    assert not blank, f"evidence rows with no derivation note: {blank[:5]}"


def test_track_b_counts_distinct_systems_not_call_rows(facts):
    """A row count could exceed 3 without three systems ever agreeing.

    The fixture used ``primary[key][c.call] += 1``, counting call *rows*. There
    are no multi-volume duplicates today, so nothing was mis-scored — but if a
    later volume re-evaluated the same (agent, KC, model system), the count
    would rise without any new system reporting a positive. Counting distinct
    systems makes a value above 3 unrepresentable.
    """
    _, primary, _, _ = facts
    for key, by_call in primary.items():
        for call, systems in by_call.items():
            assert isinstance(systems, set), "primary counts must be sets of model systems"
            assert systems <= set(PRIMARY_MODEL_SYSTEMS), f"{key}/{call}: {systems}"
            assert len(systems) <= len(PRIMARY_MODEL_SYSTEMS)


def test_no_pair_currently_relies_on_the_conflict_rule(db):
    """Documents today's state: no (agent, KC, system) is reported twice.

    If this starts failing, a volume has re-evaluated an existing pair and the
    "any Yes wins" rule in ``facts`` becomes load-bearing rather than defensive.
    """
    seen = defaultdict(set)
    for c in db.scalars(select(IarcMonographKcCall)):
        if c.model_system == OVERALL_STRENGTH or c.model_system not in PRIMARY_MODEL_SYSTEMS:
            continue
        seen[(c.agent_id, c.kcc_id, c.model_system)].add(c.call)
    conflicting = {k: v for k, v in seen.items() if len(v) > 1}
    assert not conflicting, (
        "a primary system now carries conflicting calls across volumes; "
        f"confirm the resolution rule is right for: {sorted(conflicting)[:5]}"
    )
