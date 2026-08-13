"""Evidence score helpers and HTML snippets."""

from __future__ import annotations


def _ev_colors() -> dict[int, str]:
    from hkcc.app.theme import EV_COLORS as ev

    return ev


def _theme() -> dict[str, str]:
    from hkcc.app.theme import THEME as t

    return t


# Directions that contradict, or fail to support, the score's positive reading.
# The score comes from a published strength label while the primary model
# systems reported something else; hKCC policy is that the label stands and the
# direction documents the tension (docs/KCC_EVIDENCE_RULES.md). That only works
# if the tension is visible, so these get a mark wherever a score is drawn —
# the same treatment "protective" already had. 53 cells score >= 2 this way.
DIRECTION_MARKS: dict[str, tuple[str, str]] = {
    "negative": ("&#8722;", "reported No — the score comes from the published label"),
    "equivocal": ("?", "equivocal — no convergent Yes"),
    "unspecified": ("&#183;", "no primary-system call recorded"),
}


def kcc_coverage(evidence: dict[str, int], threshold: int = 2) -> int:
    """How many characteristics reach ``threshold``. Ordinal-safe."""
    return sum(1 for v in evidence.values() if v >= threshold)


def count_at_least(evidence: dict[str, int], threshold: int) -> int:
    """Characteristics scoring at or above ``threshold``.

    Counting how many cells clear a bar makes no assumption about the spacing
    between scores, which is what the 0-4 scale supports. Prefer this over
    :func:`total_evidence` for ranking and display.
    """
    return sum(1 for v in evidence.values() if v >= threshold)


def has_evidence(evidence: dict[str, int]) -> bool:
    """True when any characteristic carries a positive score."""
    return any(v > 0 for v in evidence.values())


def total_evidence(evidence: dict[str, int]) -> int:
    """Sum of scores. **Exploratory only — do not present as a measure.**

    The 0-4 scale is ordinal: 4 ("Convincing") is not twice 2 ("Limited"), and
    the derivation rules give no basis for adding them. Worse, for the two
    count-derived tracks the mapping is ``score = count + 1``, so a sum is
    ``sum(counts) + number of assessed cells`` — it rewards breadth of
    assessment as much as strength of evidence. Real example: 2,4-D sums to 14
    against cyclophosphamide's 13, while cyclophosphamide has more cells at
    every threshold.

    Retained because a ``> 0`` test is still meaningful; use
    :func:`has_evidence` for that and :func:`count_at_least` for ranking.
    """
    return sum(evidence.values())


def evidence_fingerprint_html(
    scores: list[int | None],
    kcc_shorts: list[str] | None = None,
    directions: list[str | None] | None = None,
) -> str:
    return fingerprint_html(scores, kcc_shorts, directions=directions)


def fingerprint_html(
    scores: list[int | None],
    kcc_shorts: list[str] | None = None,
    directions: list[str | None] | None = None,
) -> str:
    """Render a KCC fingerprint.

    ``None`` marks a characteristic that was never evaluated for this agent and
    is drawn as an empty outline — distinct from score 0, which is a positive
    statement that the primary model systems were negative.

    ``directions`` is aligned with ``scores``. A ``protective`` entry is kept
    off the 0–4 heat ramp (teal ↓), matching the matrix and polar profile: the
    source reports suppression of the characteristic, not a tested negative.
    """
    ev = _ev_colors()
    theme = _theme()
    cells = []
    for i, v in enumerate(scores):
        short = kcc_shorts[i] if kcc_shorts and i < len(kcc_shorts) else None
        direction = directions[i] if directions and i < len(directions) else None
        if direction == "protective":
            title = f"{short}: protective" if short else "protective"
            # Teal glyph on a transparent cell — same semantics as the matrix ↓.
            cells.append(
                f'<span title="{title}" style="display:inline-flex;align-items:center;justify-content:center;'
                f"width:14px;height:14px;margin:1px;border-radius:2px;box-sizing:border-box;"
                f'color:{theme["teal"]};font-size:11px;font-weight:700;line-height:1">&#8595;</span>'
            )
            continue
        if v is None:
            title = f"{short}: not assessed" if short else "not assessed"
            style = f"background:transparent;border:1px dashed {theme['rule']};border-radius:2px;box-sizing:border-box"
        else:
            title = f"{short}: {v}/4" if short else f"{v}/4"
            style = f"background:{ev.get(v, ev[0])};border-radius:2px"
            if direction in DIRECTION_MARKS:
                # Same disclosure as the matrix: the score stands on its
                # published label, but the primary systems did not agree. Drawn
                # as an inset dotted outline so the heat value is still legible.
                title += f" — primary systems: {DIRECTION_MARKS[direction][1]}"
                style += f";outline:1px dotted {theme['ink']};outline-offset:-3px"
        cells.append(
            f'<span title="{title}" style="display:inline-block;width:14px;height:14px;margin:1px;{style}"></span>'
        )
    return f'<div style="display:flex;gap:2px;flex-wrap:nowrap">{"".join(cells)}</div>'


def group_chip_html(iarc_group: str | None) -> str:
    g = iarc_group or "—"
    t = _theme()
    if g == "1":
        bg, fg = t["accent"], "#fff"
    elif g == "2A":
        bg, fg = t["teal"], "#fff"
    elif g == "2B":
        bg, fg = t["paper3"], t["ink"]
    else:
        bg, fg = t["paper3"], t["muted"]
    label = "Not classified" if g == "—" else f"Group {g}"
    return (
        f'<span style="font-size:9px;padding:2px 6px;border-radius:3px;background:{bg};'
        f'color:{fg};font-family:JetBrains Mono,monospace">{label}</span>'
    )


def ev_bar_html(score: int, *, max_score: int = 4, width: int = 80) -> str:
    """Horizontal evidence bar."""
    ev = _ev_colors()
    theme = _theme()
    pct = int((score / max_score) * 100) if max_score else 0
    color = ev.get(score, ev[0])
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px">'
        f'<span style="position:relative;display:inline-block;width:{width}px;height:6px;'
        f'background:{theme["paper3"]};border-radius:2px;overflow:hidden">'
        f'<span style="position:absolute;left:0;top:0;bottom:0;width:{pct}%;background:{color}"></span></span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:{theme["muted"]}">'
        f"{score}/{max_score}</span></span>"
    )


def ev_legend_html() -> str:
    ev = _ev_colors()
    theme = _theme()
    items = "".join(
        f'<span style="display:flex;align-items:center;gap:4px;font-family:JetBrains Mono,monospace;font-size:10px">'
        f'<span style="width:12px;height:12px;background:{c};border-radius:2px"></span>{i}</span>'
        for i, c in ev.items()
    )
    na = (
        f'<span style="display:flex;align-items:center;gap:4px;font-family:JetBrains Mono,monospace;font-size:10px">'
        f'<span style="width:12px;height:12px;border:1px dashed {theme["rule"]};border-radius:2px;'
        f'box-sizing:border-box"></span>n/a</span>'
        f'<span style="display:flex;align-items:center;gap:4px;font-family:JetBrains Mono,monospace;font-size:10px">'
        f'<span style="width:12px;height:12px;color:{theme["teal"]};font-weight:700;text-align:center;'
        f'line-height:12px">&#8595;</span>protective</span>'
        f'<span style="display:flex;align-items:center;gap:4px;font-family:JetBrains Mono,monospace;font-size:10px">'
        f'<span style="width:12px;height:12px;color:{theme["ink"]};text-align:center;'
        f'line-height:12px">&#9633;</span>not used by IARC</span>'
        f'<span style="display:flex;align-items:center;gap:4px;font-family:JetBrains Mono,monospace;font-size:10px">'
        f'<span style="width:12px;height:12px;background:{ev.get(3, ev[0])};border-radius:2px;'
        f'outline:1px dotted {theme["ink"]};outline-offset:-3px;box-sizing:border-box"></span>'
        f"label &gt; primaries</span>"
    )
    return (
        f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">{items}{na}'
        f'<span style="font-size:10px;color:{theme["muted"]};margin-left:6px">'
        f"evidence 0–4 · n/a = not assessed · ↓ = reported to suppress · "
        f"□ = the IARC working group did not use this data in its evaluation · "
        f"dotted / − / ? / · = the score rests on a published label while the primary "
        f"model systems reported No, Equivocal or nothing</span></div>"
    )
