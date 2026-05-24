"""Live PubChem / screening / OpenAlex / CompTox UI (read-only integration).

All outbound calls are wrapped in ``st.cache_data(ttl=...)`` so that repeat
clicks during a user session don't hammer NCBI/OpenAlex/EPA. The underlying
clients in ``pipelines.clients.*`` stay pure (easier to unit-test); caching
lives at the UI boundary.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from pipelines.clients import ccte, openalex, pubchem

PUBCHEM_TTL = 60 * 60  # 1h — compound identity is stable
OPENALEX_TTL = 60 * 60  # 1h — works metadata changes slowly
CCTE_TTL = 30 * 60  # 30 min — chemistry dashboards


@st.cache_data(ttl=PUBCHEM_TTL, show_spinner=False)
def _cached_search_compound_by_name(name: str) -> list[int]:
    return pubchem.search_compound_by_name(name)


@st.cache_data(ttl=PUBCHEM_TTL, show_spinner=False)
def _cached_compound_properties(cid: int) -> dict:
    return pubchem.get_compound_properties(cid)


@st.cache_data(ttl=PUBCHEM_TTL, show_spinner=False)
def _cached_assay_summary(cid: int, max_rows: int) -> tuple[list[str], list[dict]]:
    return pubchem.assay_summary_table(cid, max_rows=max_rows)


@st.cache_data(ttl=OPENALEX_TTL, show_spinner=False)
def _cached_openalex_works(query: str, mailto: str, per_page: int) -> list[dict]:
    return openalex.search_works(query, mailto=mailto, per_page=per_page)


@st.cache_data(ttl=CCTE_TTL, show_spinner=False)
def _cached_ccte_keyword(keyword: str, api_key: str | None) -> dict:
    return ccte.try_chemical_keyword_search(keyword, api_key)


def render_live_feeds(*, show_header: bool = True) -> None:
    if show_header:
        st.markdown('<p class="mono">Live data</p>', unsafe_allow_html=True)
        st.subheader("External pipelines · live lookup")
        st.caption(
            "On-demand calls to public APIs. Curated hKCC scores remain in the database; "
            "this view is for discovery and provenance research only."
        )

    mailto = os.environ.get("OPENALEX_MAILTO", "")
    try:
        if hasattr(st, "secrets") and st.secrets:
            mailto = st.secrets.get("OPENALEX_MAILTO", mailto) or mailto
    except Exception:
        pass
    if not mailto:
        mailto = "hkcc@example.org"

    ccte_key = os.environ.get("EPA_CCTE_API_KEY", "")
    try:
        if hasattr(st, "secrets") and st.secrets:
            ccte_key = st.secrets.get("EPA_CCTE_API_KEY", ccte_key) or ccte_key
    except Exception:
        pass

    tab_pubchem, tab_screening, tab_openalex, tab_epa = st.tabs(
        ["PubChem", "Screening (PubChem assays)", "OpenAlex", "EPA CompTox / CCTE"]
    )

    with tab_pubchem:
        st.markdown(
            "**PubChem** — compound identifiers and properties "
            "([PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest))."
        )
        name = st.text_input("Compound name or synonym", value="benzene", key="lf_pc_name")
        if st.button("Search PubChem", key="lf_pc_go"):
            with st.spinner("Calling PubChem…"):
                try:
                    cids = _cached_search_compound_by_name(name)
                except Exception as e:
                    st.error(f"PubChem error: {e}")
                    cids = []
            if not cids:
                st.warning("No CID returned. Try another spelling or use a common synonym.")
            else:
                st.success(f"Found {len(cids)} CID(s): {', '.join(map(str, cids))}")
                cid = st.selectbox("Choose CID", cids, key="lf_pc_cid")
                try:
                    props = _cached_compound_properties(int(cid))
                    st.dataframe(pd.DataFrame([props]), use_container_width=True, hide_index=True)
                    st.link_button(
                        "Open in PubChem",
                        pubchem.pubchem_compound_url(int(cid)),
                        use_container_width=False,
                    )
                except Exception as e:
                    st.error(str(e))

    with tab_screening:
        st.markdown(
            "**Bioassay summary** — PubChem aggregates screening results from many contributors "
            "(including **Tox21** and other HTS programs). This is not a raw ToxCast API export."
        )
        cid_in = st.number_input("PubChem CID", min_value=1, value=241, step=1, key="lf_assay_cid")
        nrows = st.slider("Max rows", 10, 200, 40, key="lf_assay_n")
        if st.button("Load assay summary", key="lf_assay_go"):
            with st.spinner("Loading assay summary…"):
                try:
                    _, rows = _cached_assay_summary(int(cid_in), int(nrows))
                except Exception as e:
                    st.error(str(e))
                    rows = []
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.link_button(
                "PubChem bioassay query for this CID",
                pubchem.pubchem_bioassay_url(int(cid_in)),
            )

    with tab_openalex:
        st.markdown(
            f"**OpenAlex** — scholarly works ([API](https://docs.openalex.org)). "
            f"Using `mailto={mailto}`; set `OPENALEX_MAILTO` in Streamlit secrets."
        )
        q = st.text_input(
            "Search works",
            value="key characteristics carcinogens Smith",
            key="lf_oa_q",
        )
        n = st.slider("Results", 5, 25, 12, key="lf_oa_n")
        if st.button("Search OpenAlex", key="lf_oa_go"):
            with st.spinner("Calling OpenAlex…"):
                try:
                    works = _cached_openalex_works(q, mailto, int(n))
                except Exception as e:
                    st.error(str(e))
                    works = []
            if works:
                st.dataframe(pd.DataFrame(works), use_container_width=True, hide_index=True)

    with tab_epa:
        st.markdown(
            "**EPA CompTox / CCTE** — DSSTox and ToxCast-related chemistry. "
            f"Dashboard works without a key; REST API needs a free EPA key ([about]({ccte.CCTE_DOCS}))."
        )
        cq = st.text_input("Chemical name for dashboard link", value="benzene", key="lf_ccte_q")
        st.link_button("Open CompTox Dashboard search", ccte.comptox_search_url(cq), use_container_width=True)
        st.divider()
        st.subheader("Optional CCTE API (key required)")
        key_field = st.text_input("CCTE API key", value="", type="password", key="lf_ccte_key_ui")
        use_key = (key_field or ccte_key).strip()
        if st.button("Try CCTE keyword search", key="lf_ccte_go"):
            res = _cached_ccte_keyword(cq, use_key or None)
            if res.get("skipped"):
                st.info(res["message"])
            elif res.get("ok"):
                st.json(res.get("data", {}))
            else:
                st.warning(f"CCTE request did not succeed: {res}")

    st.caption(
        "Scheduled batch sync (Prefect) can call the same client functions later; this view only runs "
        "interactive lookups."
    )
