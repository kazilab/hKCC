"""Evidence matrix heatmap via st.components.html."""

from __future__ import annotations

from html import escape

import streamlit.components.v1 as components

from hkcc.app.utils.evidence import DIRECTION_MARKS, count_at_least, kcc_coverage


def to_matrix_row(row: dict) -> dict:
    """Adapt an API / data-client matrix row to this component's shape.

    A **rename only** — every other key is carried through untouched. The page
    used to build this dict by listing the keys it wanted::

        {"id": r["agent_id"], "name": r["agent_name"],
         "iarc_group": r.get("iarc_group"), "scores": r["scores"]}

    which silently dropped ``directions`` and ``data_roles`` when they were
    added. The component supported both and the data carried both, so the marks
    were absent from the live heat map while every unit test passed: protective
    cells painted as ordinary 0s, and 147 "Not used" cells showed no mark.

    Spreading the row means a field added to the matrix payload reaches the
    renderer without anyone remembering to widen this mapping.
    """
    return {**row, "id": row["agent_id"], "name": row["agent_name"]}


def matrix_heatmap_html(
    kccs: list[dict],
    rows: list[dict],
    *,
    matrix_style: str = "heatmap",
) -> str:
    """rows: {id, name, iarc_group, scores: {kcc_id: int}}"""
    from hkcc.app.theme import EV_COLORS, THEME

    P = THEME["paper2"]
    P3 = THEME["paper3"]
    INK = THEME["ink"]
    MUTED = THEME["muted"]
    RULE = THEME["rule"]
    ACCENT = THEME["accent"]
    cell = 32
    header_cells = "".join(
        f"""<th style="padding:0;border-bottom:1px solid {RULE};border-right:1px solid {RULE};background:{P}">
          <div style="height:120px;width:{cell}px;position:relative;display:flex;align-items:flex-end;justify-content:center">
            <span style="font-family:JetBrains Mono,monospace;font-size:9px;color:{MUTED};
              transform:rotate(-60deg);position:absolute;bottom:28px;white-space:nowrap">{escape(str(k["short"]))}</span>
            <span style="font-size:9px;font-family:JetBrains Mono,monospace;color:{INK}">{k["n"]:02d}</span>
          </div>
        </th>"""
        for k in kccs
    )
    TEAL = THEME["teal"]
    body_rows = []
    for row in rows:
        scores = row["scores"]
        directions = row.get("directions", {})
        data_roles = row.get("data_roles", {})
        cells = []
        for k in kccs:
            v = scores.get(k["id"])
            d = directions.get(k["id"], "positive")
            # The IARC working group did not use this data in its evaluation.
            # Almost all of these still score 2-4 (protective overrides score 0)
            # because the score reflects the published strength label alone.
            # Marked so a high score here is not read as "IARC relied on this".
            not_used = data_roles.get(k["id"]) == "Not used"
            # Built once so every assessed cell carries the mark, including
            # protective ones -- otherwise two cells hold the role and show
            # nothing, and the mark count silently disagrees with the data.
            role_mark = (
                f'<span style="position:absolute;top:1px;right:2px;font-size:9px;'
                f'line-height:1;color:{INK};opacity:0.75">&#9633;</span>'
                if not_used
                else ""
            )
            role_note = " — IARC data role: Not used (the working group did not use this data)" if not_used else ""
            if d == "protective":
                # The source reports the agent as *suppressing* this
                # characteristic. Rendering it on the positive heat ramp would
                # invert its meaning, so it gets its own mark.
                cells.append(
                    f'<td title="{escape(str(row["name"]))} × {escape(str(k["short"]))} = '
                    f'protective (reported to suppress this characteristic){role_note}" '
                    f'style="width:{cell}px;height:{cell}px;background:{P};position:relative;'
                    f"border-bottom:1px solid {RULE};border-right:1px solid {RULE};"
                    f"text-align:center;vertical-align:middle;color:{TEAL};"
                    f'font-size:13px;font-weight:700">{role_mark}&#8595;</td>'
                )
                continue
            if v is None:
                # Never evaluated. Left blank rather than shaded as a 0, which
                # would assert negative evidence the sources never reported.
                cells.append(
                    f'<td title="{escape(str(row["name"]))} × {escape(str(k["short"]))} = not assessed" '
                    f'style="width:{cell}px;height:{cell}px;background:{P};'
                    f"border-bottom:1px solid {RULE};border-right:1px solid {RULE};"
                    f'text-align:center;vertical-align:middle;color:{MUTED};font-size:9px">·</td>'
                )
                continue
            bg = EV_COLORS.get(v, EV_COLORS[0])
            inner = ""
            if matrix_style == "bar" and v > 0:
                pct = int((v / 4) * 100)
                bg = EV_COLORS[0]
                inner = (
                    f'<span style="display:inline-block;width:70%;height:{pct}%;min-height:2px;'
                    f'background:{ACCENT};position:relative;vertical-align:bottom"></span>'
                )
            elif matrix_style == "number" and v > 0:
                color = "#fff" if v >= 3 else INK
                inner = f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{color}">{v}</span>'
            elif matrix_style == "dot" and v > 0:
                sz = 4 + v * 2
                inner = f'<span style="width:{sz}px;height:{sz}px;border-radius:50%;background:{INK};opacity:0.85;display:inline-block"></span>'
            elif matrix_style == "heatmap":
                bg = EV_COLORS.get(v, EV_COLORS[0])
            # The score comes from a published strength label, but the primary
            # model systems reported No / Equivocal / nothing. The label stands
            # (see KCC_EVIDENCE_RULES.md), yet painting the cell as ordinary
            # positive evidence hides the tension: 53 cells score >=2 this way.
            dir_mark, dir_note = "", ""
            if d in DIRECTION_MARKS:
                glyph, wording = DIRECTION_MARKS[d]
                dir_mark = (
                    f'<span style="position:absolute;bottom:0;left:2px;font-size:9px;'
                    f'line-height:1;color:{INK};opacity:0.8;font-weight:700">{glyph}</span>'
                )
                dir_note = f" — primary systems: {wording}"
            title = f"{escape(str(row['name']))} × {escape(str(k['short']))} = {v}/4{dir_note}{role_note}"
            cells.append(
                f'<td title="{title}" style="width:{cell}px;height:{cell}px;'
                f"background:{bg};border-bottom:1px solid {RULE};border-right:1px solid {RULE};"
                f'text-align:center;vertical-align:bottom;position:relative">{role_mark}{dir_mark}{inner}</td>'
            )
        strong = count_at_least(scores, 3)
        cov = kcc_coverage(scores)
        grp = row.get("iarc_group") or "—"
        body_rows.append(
            f"""<tr>
              <td style="position:sticky;left:0;background:{P};padding:8px 12px;border-bottom:1px solid {RULE};border-right:1px solid {RULE};min-width:200px;color:{INK}">
                <span style="font-family:'Instrument Serif',serif;font-size:15px">{escape(str(row["name"]))}</span>
                <span style="font-size:9px;border:1px solid {RULE};padding:1px 5px;margin-left:6px;border-radius:3px;color:{MUTED}">{escape(str(grp))}</span>
              </td>
              {"".join(cells)}
              <td style="font-family:JetBrains Mono,monospace;font-size:11px;text-align:right;padding:0 8px;border-bottom:1px solid {RULE};color:{INK}">{strong}</td>
              <td style="font-family:JetBrains Mono,monospace;font-size:11px;text-align:right;padding:0 8px;border-bottom:1px solid {RULE};color:{INK}">{cov}/{len(kccs)}</td>
            </tr>"""
        )
    # Per-KCC count of agents reaching "limited" or better. A count, not a sum:
    # adding ordinal scores down a column has no defensible meaning.
    col_totals = [sum(1 for r in rows if (r["scores"].get(k["id"]) or 0) >= 2) for k in kccs]
    total_cells = "".join(
        f'<td style="background:{P3};font-family:JetBrains Mono,monospace;font-size:11px;text-align:center;padding:8px 0;border-right:1px solid {RULE};color:{INK}">{t}</td>'
        for t in col_totals
    )
    n_assessed = sum(len(r["scores"]) for r in rows)
    footer = f"""<tr>
      <td style="position:sticky;left:0;background:{P3};padding:10px 12px;font-family:JetBrains Mono,monospace;font-size:10px;border-right:1px solid {RULE};color:{MUTED}"
          title="Agents reaching a score of 2 or more for this characteristic">AGENTS &#8805;2</td>
      {total_cells}
      <td colspan="2" style="background:{P3};font-family:JetBrains Mono,monospace;font-size:11px;text-align:right;padding:8px;color:{INK}">{n_assessed} cells assessed</td>
    </tr>"""
    return f"""
    <div style="overflow-x:auto;border:1px solid {RULE};border-radius:4px;background:{P};font-family:Public Sans,sans-serif;color:{INK}">
      <table style="border-collapse:collapse;font-size:12px">
        <thead><tr>
          <th style="position:sticky;left:0;z-index:2;background:{P};padding:8px 12px;text-align:left;min-width:200px;border-bottom:1px solid {RULE};border-right:1px solid {RULE};color:{MUTED}">
            <span style="font-family:JetBrains Mono,monospace;font-size:10px">AGENT ({len(rows)})</span>
          </th>
          {header_cells}
          <th style="padding:8px;border-bottom:1px solid {RULE};background:{P};font-family:JetBrains Mono,monospace;font-size:10px;color:{MUTED}" title="Characteristics scoring 3 or more (substantial or convincing)">&#8805;3</th>
          <th style="padding:8px;border-bottom:1px solid {RULE};background:{P};font-family:JetBrains Mono,monospace;font-size:10px;color:{MUTED}">COVERAGE</th>
        </tr></thead>
        <tbody>{"".join(body_rows)}{footer}</tbody>
      </table>
    </div>
    """


def render_matrix(kccs: list[dict], rows: list[dict], matrix_style: str = "heatmap") -> None:
    h = min(800, 120 + len(rows) * 36)
    components.html(matrix_heatmap_html(kccs, rows, matrix_style=matrix_style), height=h, scrolling=True)
