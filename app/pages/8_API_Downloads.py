"""Data & API — mockup screen 9."""

from pathlib import Path

import httpx
import streamlit as st

from app.data.api_samples import AUTH_TIERS, ENDPOINTS, QUICKSTART
from app.data_client import api_base_url
from app.page_shell import init_page
from app.views.live_feeds import render_live_feeds
from db.config import get_settings

THEME, _ = init_page("api")

base = api_base_url()
release = get_settings().hkcc_release_tag
export_dir = Path(__file__).resolve().parents[2] / "exports" / release

st.markdown('<p class="mono">Build</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">Data & API</h1>', unsafe_allow_html=True)
st.caption(
    "hKCC is fully open. Download the dataset, query the JSON API, or contribute score proposals."
)

tab_api, tab_live = st.tabs(["REST API & downloads", "Live feeds (PubChem · OpenAlex · EPA)"])

with tab_api:
    st.markdown("#### Dataset downloads")
    dl_cols = st.columns(3)
    formats = [
        ("CSV", "kccs.csv", "Curated KCCs, agents, and evidence tables."),
        ("JSON", "manifest.json", "Release manifest and file index."),
        ("Parquet", "kccs.parquet", "Columnar format for pandas / DuckDB."),
    ]
    for col, (fmt, fname, desc) in zip(dl_cols, formats):
        fpath = export_dir / fname
        size = "—"
        if fpath.is_file():
            kb = fpath.stat().st_size / 1024
            size = f"{kb:.0f} KB" if kb < 1024 else f"{kb / 1024:.1f} MB"
        with col:
            with st.container(border=True):
                st.markdown(f'<p class="brand-serif" style="font-size:1.75rem;margin:0">{fmt}</p>', unsafe_allow_html=True)
                st.caption(desc)
                st.caption(f"{size} · {fname}")
                if fpath.is_file():
                    st.download_button(
                        f"↓ {fmt}",
                        fpath.read_bytes(),
                        file_name=f"hkcc-{release}-{fname}",
                        key=f"dl_{fmt}",
                    )
                else:
                    st.caption("Run export locally to generate files.")
                    if st.button(f"Export {release}", key=f"exp_{fmt}"):
                        try:
                            from pipelines.export_release import export_release

                            out = export_release(release)
                            st.success(f"Exported to `{out}` — refresh page.")
                        except Exception as e:
                            st.error(str(e))

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
        st.code(ep["sample"], language="json")
        st.code(f"{base}{ep['path']}", language="text")
        if st.button("Try live request"):
            try:
                if ep["method"] == "POST":
                    st.info("POST /contribute requires a JSON body — use OpenAPI docs.")
                else:
                    r = httpx.get(f"{base}{ep['path']}", timeout=10.0)
                    st.json(r.json() if r.status_code == 200 else {"error": r.text})
            except httpx.HTTPError as e:
                st.error(f"API unreachable: {e}")
        st.link_button("OpenAPI documentation", f"{base}/docs")

    st.markdown("---")
    st.markdown('<p class="eyebrow">Authentication</p>', unsafe_allow_html=True)
    st.markdown("#### API keys & rate limits")
    tier_cols = st.columns(3)
    for col, tier in zip(tier_cols, AUTH_TIERS):
        with col:
            with st.container(border=True):
                st.markdown(
                    f'<span class="mono" style="color:{THEME["accent"]}">{tier["tier"]}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{tier['title']}**")
                st.write(tier["body"])
                st.caption(tier["limit"])

    st.markdown("---")
    st.markdown('<p class="eyebrow">Snippets</p>', unsafe_allow_html=True)
    st.markdown("#### Quickstart")
    sn_cols = st.columns(2)
    for col, (lang, code) in zip(sn_cols, QUICKSTART.items()):
        with col:
            st.markdown(f"**{lang}**")
            st.code(code, language="python" if lang == "Python" else "r")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"[Resource BibTeX]({base}/api/v1/agents/citation/resource.bib)")
    with c2:
        st.markdown(f"[Resource RIS]({base}/api/v1/agents/citation/resource.ris)")

with tab_live:
    render_live_feeds(show_header=False)
