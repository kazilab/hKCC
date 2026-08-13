"""Polar evidence profile for an agent's KCC fingerprint.

This was a connected radar polygon, which had no honest way to draw a
characteristic that was never assessed: a missing value became ``0``, the vertex
collapsed to the origin, and the shape read exactly like a characteristic that
had been tested and found negative. Roughly half of all (agent, KCC) pairs are
unassessed, so that was not a rare edge case — it was the usual picture.

Two properties of the data rule the polygon out rather than merely arguing
against it:

* A gap has no defensible vertex. At the origin it asserts a negative the
  sources never reported; interpolated across, it asserts evidence nobody
  recorded.
* The ten characteristics are unordered categories. A line from KCC-01 to
  KCC-02 implies the two are adjacent on some continuum, and that the space
  between them means something. Neither is true.

So each characteristic owns an angular sector instead, filled to a radius set by
its score and coloured on the same 0-4 ramp as the matrix and the fingerprint.
Nothing is interpolated between axes, and an unassessed characteristic is drawn
as what it is: empty ground behind a dashed spoke.
"""

from __future__ import annotations

import math
from html import escape

import streamlit.components.v1 as components

from hkcc.app.utils.evidence import DIRECTION_MARKS

# Score 0 ("assessed, primary systems negative") is a real finding and must stay
# visible, but it has no radius of its own. It gets a stub just clear of the
# origin -- present, and unmistakably shorter than a score of 1.
STUB_RADIUS = 10.0
# Breathing room between neighbouring sectors so they read as discrete
# categories rather than one continuous ring.
SECTOR_PAD = 0.035


def _sector_path(cx: float, cy: float, a1: float, a2: float, radius: float) -> str:
    """A wedge from the centre spanning ``a1``-``a2`` at ``radius``."""
    x1, y1 = cx + math.cos(a1) * radius, cy + math.sin(a1) * radius
    x2, y2 = cx + math.cos(a2) * radius, cy + math.sin(a2) * radius
    # large-arc-flag is 0: with ten characteristics a sector spans 36 degrees.
    return f"M{cx:.1f},{cy:.1f} L{x1:.1f},{y1:.1f} A{radius:.1f},{radius:.1f} 0 0 1 {x2:.1f},{y2:.1f} Z"


def radar_plot_html(
    kccs: list[dict],
    evidence: dict[str, int],
    *,
    directions: dict[str, str] | None = None,
    width: int = 360,
) -> str:
    """Render the profile.

    ``evidence`` carries only the characteristics that were actually assessed;
    a key that is absent means "not assessed" and is never coerced to 0.
    ``directions`` marks cells the source reported as *protective*, which are
    kept off the positive ramp for the same reason as in the matrix.
    """
    from hkcc.app.theme import EV_COLORS, THEME

    accent = THEME["accent"]
    rule = THEME["rule"]
    muted = THEME["muted"]
    teal = THEME["teal"]
    n = len(kccs)
    cx, cy, r = 180.0, 180.0, 140.0
    if not n:
        return f'<svg viewBox="0 0 360 360" width="100%" style="max-width:{width}px"></svg>'

    directions = directions or {}
    half = math.pi / n
    rings = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r * frac:.1f}" fill="none" stroke="{rule}" stroke-width="1"/>'
        for frac in (0.25, 0.5, 0.75, 1)
    )

    spokes, sectors, labels = [], [], []
    for i, k in enumerate(kccs):
        centre = (2 * math.pi * i) / n - math.pi / 2
        a1, a2 = centre - half + SECTOR_PAD, centre + half - SECTOR_PAD
        short = escape(str(k.get("short", "")))
        v = evidence.get(k["id"])
        protective = directions.get(k["id"]) == "protective"
        assessed = v is not None or protective

        # An unassessed axis keeps a dashed spoke so the geometry stays legible,
        # but nothing is painted in its sector.
        spokes.append(
            f'<line x1="{cx}" y1="{cy}" x2="{cx + math.cos(centre) * r:.1f}" '
            f'y2="{cy + math.sin(centre) * r:.1f}" stroke="{rule}" stroke-width="1"'
            + ("" if assessed else ' stroke-dasharray="2 4"')
            + "/>"
        )

        if protective:
            # Reported to suppress this characteristic. The constraint on
            # `evidence` keeps its score at 0, so it draws at the stub -- but in
            # teal, because putting it on the positive ramp would invert it.
            sectors.append(
                f'<path d="{_sector_path(cx, cy, a1, a2, STUB_RADIUS)}" fill="{teal}" '
                f'fill-opacity="0.9" stroke="{teal}" stroke-width="1">'
                f"<title>{short}: protective (reported to suppress this characteristic)</title></path>"
            )
            labels.append((centre, teal, 1.0))
            continue

        if v is None:
            # A transparent wedge so the empty sector still answers a hover with
            # "not assessed" instead of saying nothing at all. It reaches past
            # the rings to cover the axis label too.
            sectors.append(
                f'<path d="{_sector_path(cx, cy, a1, a2, r + 22)}" fill="transparent" '
                f'pointer-events="all"><title>{short}: not assessed</title></path>'
            )
            labels.append((centre, muted, 0.45))
            continue

        radius = max(STUB_RADIUS, (v / 4.0) * r)
        fill = EV_COLORS.get(v, EV_COLORS[0])
        # A score whose primary systems reported No / Equivocal / nothing still
        # fills its sector — the published label stands — but is drawn with a
        # dashed edge and says so on hover, rather than reading as settled
        # positive evidence. Same disclosure as the matrix and fingerprint.
        direction = directions.get(k["id"], "positive")
        qualified = direction in DIRECTION_MARKS
        edge = ' stroke-dasharray="3 2"' if qualified else ""
        note = f" — primary systems: {DIRECTION_MARKS[direction][1]}" if qualified else ""
        sectors.append(
            f'<path d="{_sector_path(cx, cy, a1, a2, radius)}" fill="{fill}" '
            f'stroke="{accent}" stroke-width="0.75" stroke-opacity="0.55"{edge}>'
            f"<title>{short}: {v}/4{escape(note)}</title></path>"
        )
        labels.append((centre, muted, 1.0))

    # Tooltips live on the sector paths, never inside <text>: a nested <title>
    # is valid but some lenient renderers flow it as visible content.
    label_svg = "".join(
        f'<text x="{cx + math.cos(a) * (r + 16):.1f}" y="{cy + math.sin(a) * (r + 16):.1f}" '
        f'font-size="9.5" font-family="JetBrains Mono,monospace" fill="{color}" '
        f'opacity="{opacity}" text-anchor="middle" dominant-baseline="middle" '
        f'pointer-events="none">{k["n"]:02d}</text>'
        for k, (a, color, opacity) in zip(kccs, labels, strict=True)
    )
    return f"""
    <svg viewBox="0 0 360 360" width="100%" style="max-width:{width}px;display:block;background:transparent">
      {rings}{"".join(spokes)}
      {"".join(sectors)}
      {label_svg}
    </svg>
    """


def render_radar(
    kccs: list[dict],
    evidence: dict[str, int],
    directions: dict[str, str] | None = None,
) -> None:
    from hkcc.app.utils.evidence import ev_legend_html

    body = radar_plot_html(kccs, evidence, directions=directions)
    components.html(
        '<div style="font-family:Public Sans,sans-serif;background:transparent">'
        f'{body}<div style="margin-top:10px">{ev_legend_html()}</div></div>',
        height=460,
    )
