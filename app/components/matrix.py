"""Evidence matrix heatmap via st.components.html."""

from __future__ import annotations

import streamlit.components.v1 as components

from app.theme import THEME
from app.utils.evidence import EV_COLORS, kcc_coverage, total_evidence

P = THEME["paper2"]
P3 = THEME["paper3"]
INK = THEME["ink"]
MUTED = THEME["muted"]
RULE = THEME["rule"]


def matrix_heatmap_html(
    kccs: list[dict],
    rows: list[dict],
    *,
    matrix_style: str = "heatmap",
) -> str:
    """rows: {id, name, iarc_group, scores: {kcc_id: int}}"""
    cell = 32
    header_cells = "".join(
        f"""<th style="padding:0;border-bottom:1px solid {RULE};border-right:1px solid {RULE};background:{P}">
          <div style="height:120px;width:{cell}px;position:relative;display:flex;align-items:flex-end;justify-content:center">
            <span style="font-family:JetBrains Mono,monospace;font-size:9px;color:{MUTED};
              transform:rotate(-60deg);position:absolute;bottom:28px;white-space:nowrap">{k['short']}</span>
            <span style="font-size:9px;font-family:JetBrains Mono,monospace;color:{INK}">{k['n']:02d}</span>
          </div>
        </th>"""
        for k in kccs
    )
    body_rows = []
    for row in rows:
        scores = row["scores"]
        cells = []
        for k in kccs:
            v = scores.get(k["id"], 0)
            bg = EV_COLORS.get(v, EV_COLORS[0])
            inner = ""
            if matrix_style == "number" and v > 0:
                color = "#fff" if v >= 3 else INK
                inner = f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{color}">{v}</span>'
            elif matrix_style == "dot" and v > 0:
                sz = 4 + v * 2
                inner = f'<span style="width:{sz}px;height:{sz}px;border-radius:50%;background:{INK};opacity:0.85;display:inline-block"></span>'
            cells.append(
                f'<td title="{row["name"]} × {k["short"]} = {v}/4" style="width:{cell}px;height:{cell}px;'
                f"background:{bg};border-bottom:1px solid {RULE};border-right:1px solid {RULE};"
                f'text-align:center;vertical-align:middle">{inner}</td>'
            )
        w = total_evidence(scores)
        cov = kcc_coverage(scores)
        grp = row.get("iarc_group") or "—"
        body_rows.append(
            f"""<tr>
              <td style="position:sticky;left:0;background:{P};padding:8px 12px;border-bottom:1px solid {RULE};border-right:1px solid {RULE};min-width:200px;color:{INK}">
                <span style="font-family:'Instrument Serif',serif;font-size:15px">{row['name']}</span>
                <span style="font-size:9px;border:1px solid {RULE};padding:1px 5px;margin-left:6px;border-radius:3px;color:{MUTED}">{grp}</span>
              </td>
              {''.join(cells)}
              <td style="font-family:JetBrains Mono,monospace;font-size:11px;text-align:right;padding:0 8px;border-bottom:1px solid {RULE};color:{INK}">{w}</td>
              <td style="font-family:JetBrains Mono,monospace;font-size:11px;text-align:right;padding:0 8px;border-bottom:1px solid {RULE};color:{INK}">{cov}/14</td>
            </tr>"""
        )
    col_totals = [sum(r["scores"].get(k["id"], 0) for r in rows) for k in kccs]
    total_cells = "".join(
        f'<td style="background:{P3};font-family:JetBrains Mono,monospace;font-size:11px;text-align:center;padding:8px 0;border-right:1px solid {RULE};color:{INK}">{t}</td>'
        for t in col_totals
    )
    sigma = sum(col_totals)
    max_score = len(rows) * len(kccs) * 4 if rows else 0
    footer = f"""<tr>
      <td style="position:sticky;left:0;background:{P3};padding:10px 12px;font-family:JetBrains Mono,monospace;font-size:10px;border-right:1px solid {RULE};color:{MUTED}">COLUMN WEIGHT</td>
      {total_cells}
      <td colspan="2" style="background:{P3};font-family:JetBrains Mono,monospace;font-size:11px;text-align:right;padding:8px;color:{INK}">Σ {sigma} / {max_score}</td>
    </tr>"""
    return f"""
    <div style="overflow-x:auto;border:1px solid {RULE};border-radius:4px;background:{P};font-family:Public Sans,sans-serif;color:{INK}">
      <table style="border-collapse:collapse;font-size:12px">
        <thead><tr>
          <th style="position:sticky;left:0;z-index:2;background:{P};padding:8px 12px;text-align:left;min-width:200px;border-bottom:1px solid {RULE};border-right:1px solid {RULE};color:{MUTED}">
            <span style="font-family:JetBrains Mono,monospace;font-size:10px">AGENT ({len(rows)})</span>
          </th>
          {header_cells}
          <th style="padding:8px;border-bottom:1px solid {RULE};background:{P};font-family:JetBrains Mono,monospace;font-size:10px;color:{MUTED}">WEIGHT</th>
          <th style="padding:8px;border-bottom:1px solid {RULE};background:{P};font-family:JetBrains Mono,monospace;font-size:10px;color:{MUTED}">COVERAGE</th>
        </tr></thead>
        <tbody>{''.join(body_rows)}{footer}</tbody>
      </table>
    </div>
    """


def render_matrix(kccs: list[dict], rows: list[dict], matrix_style: str = "heatmap") -> None:
    h = min(800, 120 + len(rows) * 36)
    components.html(matrix_heatmap_html(kccs, rows, matrix_style=matrix_style), height=h, scrolling=True)
