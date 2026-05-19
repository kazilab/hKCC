"""Radar plot for agent KCC fingerprint."""

from __future__ import annotations

import streamlit.components.v1 as components


def radar_plot_html(
    kccs: list[dict],
    evidence: dict[str, int],
    *,
    width: int = 360,
    height: int = 380,
) -> str:
    n = len(kccs)
    cx, cy, r = 180, 180, 140
    pts = []
    for i, k in enumerate(kccs):
        import math

        angle = (2 * math.pi * i) / n - math.pi / 2
        v = evidence.get(k["id"], 0) / 4.0
        pts.append(
            {
                "x": cx + math.cos(angle) * r * v,
                "y": cy + math.sin(angle) * r * v,
                "ax": cx + math.cos(angle) * r,
                "ay": cy + math.sin(angle) * r,
                "n": k["n"],
                "label_x": cx + math.cos(angle) * (r + 16),
                "label_y": cy + math.sin(angle) * (r + 16),
            }
        )
    rings = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r * frac}" fill="none" stroke="#DDD6C5" stroke-width="1"/>'
        for frac in (1, 0.75, 0.5, 0.25)
    )
    spokes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{p["ax"]:.1f}" y2="{p["ay"]:.1f}" stroke="#DDD6C5" stroke-width="1"/>'
        for p in pts
    )
    poly = " ".join(f'{p["x"]:.1f},{p["y"]:.1f}' for p in pts)
    dots = "".join(f'<circle cx="{p["x"]:.1f}" cy="{p["y"]:.1f}" r="3" fill="#8B2E2A"/>' for p in pts)
    labels = "".join(
        f'<text x="{p["label_x"]:.1f}" y="{p["label_y"]:.1f}" font-size="9.5" '
        f'font-family="JetBrains Mono,monospace" fill="#6B6557" text-anchor="middle" '
        f'dominant-baseline="middle">{p["n"]:02d}</text>'
        for p in pts
    )
    return f"""
    <svg viewBox="0 0 360 360" width="100%" style="max-width:{width}px;display:block">
      {rings}{spokes}
      <polygon points="{poly}" fill="#8B2E2A" fill-opacity="0.18" stroke="#8B2E2A" stroke-width="1.5"/>
      {dots}{labels}
    </svg>
    """


def render_radar(kccs: list[dict], evidence: dict[str, int]) -> None:
    components.html(
        f'<div style="font-family:Public Sans,sans-serif">{radar_plot_html(kccs, evidence)}</motionless>'.replace(
            "motionless", "div"
        ),
        height=400,
    )
