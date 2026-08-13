"""HTML agent table with inline KCC fingerprints."""

from __future__ import annotations

from html import escape
from urllib.parse import quote

import streamlit.components.v1 as components

from hkcc.app.theme import THEME
from hkcc.app.utils.evidence import fingerprint_html, group_chip_html, kcc_coverage


def agent_table_html(
    rows: list[dict],
    *,
    kcc_shorts: list[str] | None = None,
) -> str:
    """Build clickable table. Each row needs: id, name, cas, agent_type, iarc_group, sites, scores."""
    t = THEME
    # `agent_sites` holds no rows in the shipped dataset, so this column was a
    # header above 171 em dashes. It appears only when there is something to put
    # in it, rather than advertising a field the database cannot answer.
    show_sites = any(r.get("sites") for r in rows)
    sites_header = '<th style="text-align:left;padding:8px">Tumour sites</th>' if show_sites else ""
    header = f"""
    <tr style="background:{t["paper3"]};color:{t["muted"]};font-family:JetBrains Mono,monospace;font-size:10px">
      <th style="text-align:left;padding:8px 12px">Agent</th>
      <th style="padding:8px">CAS</th>
      <th style="padding:8px">Type</th>
      <th style="padding:8px">IARC</th>
      {sites_header}
      <th style="padding:8px">KCC fingerprint</th>
      <th style="padding:8px">Coverage</th>
    </tr>"""
    body = []
    for r in rows:
        scores = r.get("scores", [])
        # Parallel list of directions (aligned with scores), when the caller
        # supplies them — protective cells must not paint as ordinary zeros.
        fp = fingerprint_html(scores, kcc_shorts, directions=r.get("directions"))
        sites_cell = (
            f'<td style="padding:8px;font-size:12px;color:{t["ink2"]}">'
            f"{escape(', '.join((r.get('sites') or [])[:3]) or '—')}</td>"
            if show_sites
            else ""
        )
        ev = r.get("evidence", {})
        # An agent with no evidence rows at all has not been scored — distinct
        # from one scored low. "0/10" would read as an assessed zero.
        #
        # The denominator is read from the ontology in use, never a literal.
        # This fell back to 14, which survived the restructure that moved the
        # four extended characteristics into Layer 2: it would have rated every
        # agent against four cells that no longer exist and hold no data.
        n_kccs = len(kcc_shorts) if kcc_shorts else len(scores)
        if not ev:
            cov_label = "not scored"
        else:
            cov_label = f"{kcc_coverage(ev)}/{n_kccs}" if n_kccs else str(kcc_coverage(ev))

        # 13 agents — including PCBs (Group 1), aniline and dichloromethane —
        # have no scored evidence at all because neither IARC source covers
        # them. Their fingerprint is a row of empty outlines, which reads as
        # "investigated and empty" unless the row says otherwise.
        unscored_badge = ""
        if not ev:
            unscored_badge = (
                f'<span title="Neither IARC source scores this agent; the characteristics are '
                f'not assessed, not negative" style="font-size:9px;padding:2px 6px;border-radius:3px;'
                f"border:1px dashed {t['rule']};color:{t['muted']};font-family:JetBrains Mono,monospace;"
                f'margin-left:6px;white-space:nowrap">no scored evidence</span>'
            )
        chip = group_chip_html(r.get("iarc_group"))
        aid = r["id"]
        body.append(
            # Rows were mouse-only: no tab stop, no role, no key handler, so the
            # table was unreachable by keyboard and unannounced to a screen
            # reader. `Enter` and `Space` now activate the row, as for a button.
            f'<tr class="hkcc-agent-row" role="button" tabindex="0"'
            f' aria-label="Open {escape(str(r["name"]))}"'
            f' style="border-bottom:1px solid {t["rule"]};cursor:pointer"'
            # aid lands in a JS string inside an HTML attribute: percent-encode
            # for the query string, then escape for the attribute.
            f" onclick=\"window.parent.location.search='?agent_id={escape(quote(str(aid)))}'\""
            f" onkeydown=\"if(event.key==='Enter'||event.key===' '){{event.preventDefault();"
            f"window.parent.location.search='?agent_id={escape(quote(str(aid)))}'}}\">"
            f'<td style="padding:10px 12px;font-family:Instrument Serif,serif;font-size:16px;color:{t["ink"]}">'
            f"{escape(str(r['name']))}{unscored_badge}</td>"
            f'<td style="padding:8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{t["muted"]}">'
            f"{escape(str(r.get('cas') or '—'))}</td>"
            f'<td style="padding:8px;font-size:12px;color:{t["ink2"]}">{escape(str(r.get("agent_type", "")))}</td>'
            f'<td style="padding:8px">{chip}</td>'
            f"{sites_cell}"
            f'<td style="padding:8px">{fp}</td>'
            f'<td style="padding:8px;font-family:JetBrains Mono,monospace;font-size:12px;text-align:center">'
            f"{cov_label}</td></tr>"
        )
    return f"""
    <div style="overflow-x:auto;border:1px solid {t["rule"]};border-radius:4px;background:{t["paper2"]}">
      <table style="width:100%;border-collapse:collapse">{header}{"".join(body)}</table>
    </div>
    """


def render_agent_table(rows: list[dict], *, kcc_shorts: list[str] | None = None) -> None:
    h = min(600, 48 + len(rows) * 44)
    components.html(agent_table_html(rows, kcc_shorts=kcc_shorts), height=h, scrolling=True)
