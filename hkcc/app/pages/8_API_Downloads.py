"""Data & API explorer."""

import base64
import html

import httpx
import streamlit as st
import streamlit.components.v1 as components

from hkcc.app.data.api_samples import ACCESS_NOTES, ENDPOINTS, quickstart
from hkcc.app.data_client import api_base_url, configured_api_base
from hkcc.app.page_shell import init_page
from hkcc.app.views.live_feeds import render_live_feeds
from hkcc.db.config import export_dir, get_settings

THEME, _ = init_page("api")

# Only a configured API has a public URL. Without one the page documents the
# interface without handing visitors links to their own machine.
api_base = configured_api_base()
base = api_base or api_base_url()
release = get_settings().release_tag
export_root = export_dir() / release


def _copyable_code(
    code: str,
    *,
    label: str,
    button_label: str = "Copy",
    dark: bool = False,
    height: int | None = None,
) -> None:
    bg = THEME["ink"] if dark else THEME["paper2"]
    fg = THEME["paper"] if dark else THEME["ink2"]
    head_bg = THEME["ink2"] if dark else THEME["paper3"]
    rule = THEME["rule"]
    accent = THEME["accent"]
    code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    escaped = html.escape(code)
    h = height or min(520, 96 + len(code.splitlines()) * 22)
    components.html(
        f"""
        <div style="border:1px solid {rule};border-radius:4px;overflow:hidden;background:{bg};font-family:Public Sans,sans-serif">
          <div style="display:flex;align-items:center;justify-content:space-between;padding:9px 12px;background:{head_bg};border-bottom:1px solid {rule}">
            <span style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:{fg}">{html.escape(label)}</span>
            <button data-code="{code_b64}" onclick='navigator.clipboard.writeText(atob(this.dataset.code)); this.textContent="Copied"; setTimeout(() => this.textContent="{html.escape(button_label)}", 1200);'
              style="border:0;background:transparent;color:{accent};font-family:JetBrains Mono,monospace;font-size:10px;cursor:pointer">{html.escape(button_label)}</button>
          </div>
          <pre style="margin:0;padding:16px;max-height:420px;overflow:auto;background:{bg};color:{fg};font-family:JetBrains Mono,ui-monospace,monospace;font-size:11.5px;line-height:1.6;white-space:pre-wrap">{escaped}</pre>
        </div>
        """,
        height=h,
        scrolling=True,
    )


st.markdown('<p class="mono">Build</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">Data & API</h1>', unsafe_allow_html=True)
st.caption("Download the dataset, query the JSON API, or submit a score proposal. No account or key required.")

tab_api, tab_live = st.tabs(["REST API & downloads", "Live feeds (PubChem · OpenAlex · EPA)"])

with tab_api:
    if not api_base:
        st.info(
            "This deployment serves the app directly from the bundled database — there is no "
            "public API endpoint. The reference below documents the interface you get by "
            "running `hkcc api` locally (or set `API_BASE_URL` to point at your own instance)."
        )
    st.markdown("#### Dataset downloads")
    dl_cols = st.columns(3)
    formats = [
        ("CSV", f"hkcc-{release}.csv.zip", "KCCs, agents, and evidence tables."),
        ("JSON", f"hkcc-{release}.json", "Full normalized dataset with provenance metadata."),
        ("Parquet", f"hkcc-{release}.parquet.zip", "Columnar format for pandas / DuckDB."),
    ]
    for col, (fmt, fname, desc) in zip(dl_cols, formats):
        fpath = export_root / fname
        size = "—"
        if fpath.is_file():
            kb = fpath.stat().st_size / 1024
            size = f"{kb:.0f} KB" if kb < 1024 else f"{kb / 1024:.1f} MB"
        with col:
            with st.container(border=True):
                st.markdown(
                    f'<p class="brand-serif" style="font-size:1.75rem;margin:0">{fmt}</p>', unsafe_allow_html=True
                )
                st.caption(desc)
                st.caption(f"{size} · {fname}")
                if fpath.is_file():
                    st.download_button(
                        f"↓ {fmt}",
                        fpath.read_bytes(),
                        file_name=fname,
                        key=f"dl_{fmt}",
                    )
                else:
                    # No "generate it now" button: this page is public, and
                    # running an export writes ~30 files plus a database row on
                    # the server for whoever clicks it.
                    st.caption("Not published for this release.")

    st.markdown("---")
    st.markdown('<p class="eyebrow">API endpoints</p>', unsafe_allow_html=True)

    if "api_endpoint" not in st.session_state:
        st.session_state["api_endpoint"] = "agents"

    left, right = st.columns([1, 2])
    with left:
        for key, ep in ENDPOINTS.items():
            active = st.session_state["api_endpoint"] == key
            label = f"{ep['method']}  {ep['path']}"
            if st.button(label, key=f"ep_{key}", use_container_width=True, type="primary" if active else "secondary"):
                st.session_state["api_endpoint"] = key
        ep = ENDPOINTS[st.session_state["api_endpoint"]]
        st.caption(ep["desc"])

    with right:
        ep = ENDPOINTS[st.session_state["api_endpoint"]]
        st.markdown(f"#### {ep['method']} `{ep['path']}`")
        _copyable_code(ep["sample"], label="Sample response", dark=True)
        if api_base:
            _copyable_code(f"{api_base}{ep['path']}", label="Request URL", height=96)
            if ep["method"] == "GET" and st.button("Try live request"):
                try:
                    r = httpx.get(f"{api_base}{ep['path']}", timeout=10.0)
                    st.json(r.json() if r.status_code == 200 else {"error": r.text})
                except httpx.HTTPError as e:
                    st.error(f"API unreachable: {e}")
            st.link_button("OpenAPI documentation", f"{api_base}/docs")
        else:
            _copyable_code(ep["path"], label="Path", height=96)

    st.markdown("---")
    st.markdown('<p class="eyebrow">Access</p>', unsafe_allow_html=True)
    st.markdown("#### How access works")
    note_cols = st.columns(len(ACCESS_NOTES))
    for col, note in zip(note_cols, ACCESS_NOTES):
        with col:
            with st.container(border=True):
                st.markdown(f"**{note['title']}**")
                st.write(note["body"])

    st.markdown("---")
    st.markdown('<p class="eyebrow">Snippets</p>', unsafe_allow_html=True)
    st.markdown("#### Quickstart")
    sn_cols = st.columns(2)
    for col, (lang, code) in zip(sn_cols, quickstart(base).items()):
        with col:
            _copyable_code(code, label=lang, button_label="Copy ↗", height=260)

    st.markdown("---")
    if api_base:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"[Resource BibTeX]({api_base}/api/v1/agents/citation/resource.bib)")
        with c2:
            st.markdown(f"[Resource RIS]({api_base}/api/v1/agents/citation/resource.ris)")
    else:
        st.caption(
            "Citation exports are served by the API: run `hkcc api`, then fetch "
            "`/api/v1/agents/citation/resource.bib` or `.ris`."
        )

with tab_live:
    render_live_feeds(show_header=False)
