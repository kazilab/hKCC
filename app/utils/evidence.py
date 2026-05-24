"""Evidence score helpers and HTML snippets."""

from __future__ import annotations


def _ev_colors() -> dict[int, str]:
    from app.theme import EV_COLORS as ev

    return ev


def _theme() -> dict[str, str]:
    from app.theme import THEME as t

    return t


def kcc_coverage(evidence: dict[str, int], threshold: int = 2) -> int:
    return sum(1 for v in evidence.values() if v >= threshold)


def total_evidence(evidence: dict[str, int]) -> int:
    return sum(evidence.values())


def evidence_fingerprint_html(scores: list[int], kcc_shorts: list[str] | None = None) -> str:
    return fingerprint_html(scores, kcc_shorts)


def fingerprint_html(scores: list[int], kcc_shorts: list[str] | None = None) -> str:
    ev = _ev_colors()
    cells = []
    for i, v in enumerate(scores):
        title = f"{kcc_shorts[i]}: {v}/4" if kcc_shorts and i < len(kcc_shorts) else f"{v}/4"
        cells.append(
            f'<span title="{title}" style="display:inline-block;width:14px;height:14px;'
            f"background:{ev.get(v, ev[0])};border-radius:2px;margin:1px\"></span>"
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
    """Horizontal evidence bar (mockup EvBar)."""
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
    return (
        f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">{items}'
        f'<span style="font-size:10px;color:{theme["muted"]};margin-left:6px">evidence 0–4</span></div>'
    )
