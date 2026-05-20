"""Data & API — mockup screen 9."""

import httpx
import streamlit as st

from app.data_client import api_base_url
from app.theme import HKCC_CSS
from app.views.live_feeds import render_live_feeds
from db.config import get_settings

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

base = api_base_url()
release = get_settings().hkcc_release_tag

st.markdown('<p class="mono">Build</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">Data & API</h1>', unsafe_allow_html=True)
st.caption("Programmatic access to curated KCC evidence. Data CC-BY-4.0 · code MIT.")

tab_api, tab_live = st.tabs(["REST API", "Live feeds (PubChem · OpenAlex · EPA)"])

with tab_api:
    endpoint = st.selectbox(
        "Endpoint",
        ["agents", "kccs", "matrix", "assays", "contribute"],
        format_func=lambda e: {
            "agents": "GET /api/v1/agents",
            "kccs": "GET /api/v1/kccs",
            "matrix": "GET /api/v1/matrix",
            "assays": "GET /api/v1/assays",
            "contribute": "POST /api/v1/contribute",
        }[e],
    )

    paths = {
        "agents": "/api/v1/agents",
        "kccs": "/api/v1/kccs",
        "matrix": "/api/v1/matrix",
        "assays": "/api/v1/assays",
        "contribute": "/api/v1/contribute",
    }
    path = paths[endpoint]
    st.code(f"{base}{path}", language="text")

    if st.button("Try live request"):
        try:
            if endpoint == "contribute":
                st.info("POST /contribute requires a JSON body — use OpenAPI docs for interactive submit.")
            else:
                r = httpx.get(f"{base}{path}", timeout=10.0)
                st.json(r.json() if r.status_code == 200 else {"error": r.text})
        except httpx.HTTPError as e:
            st.error(f"API unreachable: {e}")

    st.markdown("---")
    st.subheader("Dataset downloads")
    st.write(f"Current release tag: **{release}**")
    if st.button("Export release snapshot (local DB)"):
        try:
            from pipelines.export_release import export_release

            out = export_release(release)
            st.success(f"Exported to `{out}`")
        except Exception as e:
            st.error(str(e))

    st.markdown("---")
    st.subheader("Citations")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"[Resource BibTeX]({base}/api/v1/agents/citation/resource.bib)")
    with c2:
        st.markdown(f"[Resource RIS]({base}/api/v1/agents/citation/resource.ris)")

    st.link_button("OpenAPI documentation", f"{base}/docs", use_container_width=True)

with tab_live:
    render_live_feeds(show_header=False)
