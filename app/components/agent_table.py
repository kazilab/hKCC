"""HTML agent table with inline KCC fingerprints."""

from __future__ import annotations

import streamlit.components.v1 as components

from app.theme import THEME
from app.utils.evidence import fingerprint_html, group_chip_html, kcc_coverage


def agent_table_html(
    rows: list[dict],
    *,
    kcc_shorts: list[str] | None = None,
) -> str:
    """Build clickable table. Each row needs: id, name, cas, agent_type, iarc_group, sites, scores."""
    t = THEME
    header = f"""
    <tr style="background:{t['paper3']};color:{t['muted']};font-family:JetBrains Mono,monospace;font-size:10px">
      <th style="text-align:left;padding:8px 12px">Agent</th>
      <th style="padding:8px">CAS</th>
      <th style="padding:8px">Type</th>
      <th style="padding:8px">IARC</th>
      <th style="text-align:left;padding:8px">Tumour sites</th>
      <th style="padding:8px">KCC fingerprint</th>
      <th style="padding:8px">Coverage</th>
    </tr>"""
    body = []
    for r in rows:
        scores = r.get("scores", [])
        fp = fingerprint_html(scores, kcc_shorts)
        sites = ", ".join((r.get("sites") or [])[:3]) or "—"
        ev = r.get("evidence", {})
        cov_label = f"{kcc_coverage(ev)}/14"
        chip = group_chip_html(r.get("iarc_group"))
        aid = r["id"]
        body.append(
            f'<tr class="hkcc-agent-row" style="border-bottom:1px solid {t["rule"]};cursor:pointer"'
            f' onclick="window.parent.location.search=\'?agent_id={aid}\'">'
            f'<td style="padding:10px 12px;font-family:Instrument Serif,serif;font-size:16px;color:{t["ink"]}">'
            f'{r["name"]}</td>'
            f'<td style="padding:8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{t["muted"]}">'
            f'{r.get("cas", "—")}</td>'
            f'<td style="padding:8px;font-size:12px;color:{t["ink2"]}">{r.get("agent_type", "")}</td>'
            f'<td style="padding:8px">{chip}</td>'
            f'<td style="padding:8px;font-size:12px;color:{t["ink2"]}">{sites}</td>'
            f'<td style="padding:8px">{fp}</td>'
            f'<td style="padding:8px;font-family:JetBrains Mono,monospace;font-size:12px;text-align:center">'
            f'{cov_label}</td></tr>'
        )
    return f"""
    <div style="overflow-x:auto;border:1px solid {t['rule']};border-radius:4px;background:{t['paper2']}">
      <table style="width:100%;border-collapse:collapse">{header}{"".join(body)}</table>
    </div>
    """


def render_agent_table(rows: list[dict], *, kcc_shorts: list[str] | None = None) -> None:
    h = min(600, 48 + len(rows) * 44)
    components.html(agent_table_html(rows, kcc_shorts=kcc_shorts), height=h, scrolling=True)
