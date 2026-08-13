"""Literature reference card HTML."""

from __future__ import annotations

from html import escape

import streamlit.components.v1 as components

from hkcc.app.theme import THEME


def ref_card_html(ref: dict) -> str:
    t = THEME
    external_attrs = 'target="_blank" rel="noopener noreferrer"'
    year = ref.get("year") or "—"
    tags = ref.get("tags", [])
    tag_html = ""
    if tags:
        tag = tags[0]
        tag_html = (
            f'<span style="font-size:9px;padding:2px 6px;border:1px solid {t["rule"]};'
            f'border-radius:3px;margin-left:8px;color:{t["muted"]}">{tag}</span>'
        )
    source = ref.get("source") or ""
    source_html = ""
    if source:
        source_html = (
            f'<span style="font-size:9px;padding:2px 6px;border:1px solid {t["rule"]};'
            f'border-radius:3px;margin-left:4px;color:{t["muted"]};text-transform:uppercase">{source}</span>'
        )
    doi = ref.get("doi") or ""
    doi_line = ""
    if doi and doi != "—":
        doi_clean = doi.replace("https://doi.org/", "")
        doi_line = (
            f'<a href="https://doi.org/{doi_clean}" {external_attrs} style="color:{t["accent"]};'
            f'font-size:11px">doi:{doi_clean}</a>'
        )
    pmid = ref.get("pmid") or ""
    pmid_line = ""
    if pmid:
        pmid_line = (
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" {external_attrs} style="color:{t["accent"]};'
            f'font-size:11px;margin-left:10px">pmid:{pmid}</a>'
        )
    # `None` means the citation count was never recorded, which is not the same
    # claim as "cited zero times" — 0 cites reads as a judgement on the paper.
    raw_cites = ref.get("citations")
    cites_label = f"{raw_cites} cites" if isinstance(raw_cites, int) else "cites n/a"
    journal = ref.get("journal") or ""
    vol = ref.get("vol") or ""
    journal_html = ""
    if journal and journal != "—":
        journal_html = (
            f'<div style="font-size:12px;color:{t["ink2"]};margin-top:4px">'
            f'<em>{journal}</em>{", " + vol if vol else ""}</div>'
        )
    return f"""
    <article style="padding:14px 0;border-top:1px solid {t['rule']};font-family:Public Sans,sans-serif">
      <div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap">
        <span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{t['accent']}">{year}</span>
        {tag_html}{source_html}
        <span style="margin-left:auto;font-family:JetBrains Mono,monospace;font-size:10px;color:{t['muted']}">{cites_label}</span>
      </div>
      <div style="font-family:Instrument Serif,serif;font-size:1.15rem;line-height:1.25;margin-top:8px;font-style:italic;color:{t['ink']}">{escape(str(ref['title']))}</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{t['muted']};margin-top:6px">{ref['authors']}</div>
      {journal_html}
      {f'<div style="margin-top:6px">{doi_line}{pmid_line}</div>' if (doi_line or pmid_line) else ''}
    </article>
    """


def render_ref_cards(refs: list[dict], *, height: int | None = None) -> None:
    if not refs:
        return
    html = f'<div style="background:transparent">{"".join(ref_card_html(r) for r in refs)}</div>'
    h = height or min(800, 80 + len(refs) * 110)
    components.html(html, height=h, scrolling=True)
