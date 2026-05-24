"""Stub: periodic PubChem sync (Prefect optional).

Live compound + assay lookups use ``pipelines.clients.pubchem`` (Streamlit **Live feeds** page).
"""


def run() -> None:
    raise NotImplementedError(
        "PubChem batch pipeline scheduled for v1.1 — use pipelines.clients.pubchem for live calls."
    )
