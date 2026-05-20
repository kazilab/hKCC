"""Evidence score helpers and HTML snippets."""

from __future__ import annotations

from app.theme import EV_COLORS, THEME


def kcc_coverage(evidence: dict[str, int], threshold: int = 2) -> int:
    return sum(1 for v in evidence.values() if v >= threshold)


def total_evidence(evidence: dict[str, int]) -> int:
    return sum(evidence.values())


def evidence_fingerprint_html(scores: list[int], kcc_shorts: list[str] | None = None) -> str:
    cells = []
    for i, v in enumerate(scores):
        title = f"{kcc_shorts[i]}: {v}/4" if kcc_shorts and i < len(kcc_shorts) else f"{v}/4"
        cells.append(
            f'<span title="{title}" style="display:inline-block;width:14px;height:14px;'
            f"background:{EV_COLORS.get(v, EV_COLORS[0])};border-radius:2px;margin:1px\"></span>"
        )
    return f'<motionless style="display:flex;gap:2px;flex-wrap:nowrap">{"".join(cells)}</motionless>'.replace(
        "motionless", "div"
    )


def ev_legend_html() -> str:
    items = "".join(
        f'<span style="display:flex;align-items:center;gap:4px;font-family:JetBrains Mono,monospace;font-size:10px">'
        f'<span style="width:12px;height:12px;background:{c};border-radius:2px"></span>{i}</span>'
        for i, c in EV_COLORS.items()
    )
    return (
        f'<div style="display:flex;gap:10px;align-items:center">{items}'
        f'<span style="font-size:10px;color:{THEME["muted"]};margin-left:6px">evidence 0–4</span></div>'
    )
