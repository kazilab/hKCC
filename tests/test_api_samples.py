"""Keep the Data & API page truthful about the API it documents.

The page used to advertise PUBLIC/RESEARCHER/CURATOR tiers with API keys, ORCID
auth and webhooks — none of which exist — and its sample bodies showed a
``{"count": N, "items": [...]}`` envelope the routers never returned. These
tests compare the documented samples against real responses and fail if the two
diverge again.
"""

from __future__ import annotations

import json
import re

from hkcc.app.data.api_samples import ACCESS_NOTES, ENDPOINTS, quickstart


def _sample_json(key: str):
    raw = ENDPOINTS[key]["sample"]
    # the contribute sample documents request and response, separated by comments
    raw = "\n".join(line for line in raw.splitlines() if not line.strip().startswith("//"))
    return json.loads(raw.split("\n\n")[0]) if raw.strip() else None


def test_array_endpoints_are_documented_as_arrays(client):
    """/agents, /kccs and /assays return a bare JSON array, not an envelope."""
    for key, path in [("agents", "/api/v1/agents"), ("kccs", "/api/v1/kccs"), ("assays", "/api/v1/assays")]:
        live = client.get(path).json()
        assert isinstance(live, list), f"{path} no longer returns a list"
        documented = _sample_json(key)
        assert isinstance(documented, list), f"{key} sample must be a JSON array like the real response"


def test_documented_agent_fields_match_the_schema(client):
    """Every key in the agents sample must exist on a real response object."""
    client.get("/api/v1/agents")  # ensure the route is exercised
    from hkcc.api.schemas import AgentOut

    documented = set(_sample_json("agents")[0])
    real = set(AgentOut.model_fields)
    assert documented <= real, f"sample documents fields the API does not return: {documented - real}"


def test_documented_matrix_shape_matches(client):
    documented = _sample_json("matrix")
    assert set(documented) == {"kcc_ids", "rows"}
    assert set(documented["rows"][0]) == {"agent_id", "agent_name", "iarc_group", "scores"}


def test_no_fictional_authentication_claims():
    """The page must not promise capabilities the API does not have.

    Saying "there are no API keys" is fine and desirable; offering a *free API
    key*, an ORCID tier or webhook subscriptions is not, because none of that is
    implemented.
    """
    text = " ".join(n["title"] + " " + n["body"] for n in ACCESS_NOTES).lower()

    # Vocabulary that only appears when inventing an access-tier scheme.
    for phantom in ("orcid", "webhook", "researcher tier", "curator tier", "editorial board"):
        assert phantom not in text, f"access notes still advertise {phantom!r}"

    # Quantitative promises the application does not enforce for reads.
    assert not re.search(r"\d[\d\s,]*\s*(req|requests)\s*/\s*(hour|hr|min)", text), (
        "access notes quote a read rate limit the API does not implement"
    )

    # And it must state the actual position plainly.
    assert "unauthenticated" in text or "no authentication" in text


def test_quickstart_uses_the_configured_base_url():
    """Snippets must not hard-code localhost."""
    snippets = quickstart("https://api.example.org")
    for lang, code in snippets.items():
        assert "https://api.example.org" in code, f"{lang} snippet ignores the base URL"
        assert "localhost" not in code, f"{lang} snippet hard-codes localhost"


def test_every_documented_endpoint_path_exists(client):
    """A documented path must resolve to a registered route.

    This used to end in ``or True``, so the whole assertion was a no-op and a
    documented path that routed nowhere would still pass. Routes are now checked
    against the app's own routing table, which distinguishes "no such route"
    from "route exists, this id is absent from the test database".
    """
    # From the OpenAPI schema, not `app.routes`: this FastAPI version keeps
    # included routers nested, so walking `app.routes` finds only the top level.
    registered = set(client.get("/openapi.json").json()["paths"])
    assert registered, "no routes registered — the check would be vacuous"

    for key, ep in ENDPOINTS.items():
        if ep["method"] != "GET":
            continue
        # Documented paths carry concrete ids (…/agents/benzene-iarc); the schema
        # holds templates (…/agents/{agent_id}). Match exactly, or on the prefix
        # up to the first path parameter.
        assert any(
            ep["path"] == path
            or (
                "{" in path
                and ep["path"].startswith(path.split("{")[0])
                and ep["path"] != path.split("{")[0]
            )
            for path in registered
        ), f"{key}: {ep['path']} matches no registered route"

        response = client.get(ep["path"])
        assert response.status_code < 500, f"{key}: {ep['path']} returned {response.status_code}"
