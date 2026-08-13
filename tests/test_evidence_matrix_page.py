"""What the Evidence Matrix page renders, not what its component can render.

The heat map supported protective ``↓`` and "Not used" ``□`` marks, the API and
data client both carried the fields, and the component-level test passed — but
the page rebuilt each row by listing the keys it wanted::

    {"id": r["agent_id"], "name": r["agent_name"],
     "iarc_group": r.get("iarc_group"), "scores": r["scores"]}

so ``directions`` and ``data_roles`` never reached the renderer. The live matrix
painted coffee's protective cells as ordinary 0s and showed none of the 147
"Not used" marks.

The bug survived because ``tests/test_data_quality.py`` fed the component full
``get_matrix()`` rows, exercising the component and skipping the page wiring
entirely. These tests read the HTML the page actually hands to the browser.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hkcc.app import data_client
from hkcc.app.components.matrix import matrix_heatmap_html, to_matrix_row

PAGE = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "5_Evidence_Matrix.py"

NOT_USED_MARK = "&#9633;"
PROTECTIVE_MARK = "&#8595;"


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


@pytest.fixture(scope="module")
def page():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(PAGE), default_timeout=180)
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    return app


def _rendered_matrix(app) -> str:
    """The heat map exactly as the page hands it to the browser.

    ``components.html`` output lands in an IFrame proto's ``srcdoc``. Asserting
    on ``matrix_heatmap_html`` directly is what let the stripped rows through.
    """
    for element in app.main:
        srcdoc = getattr(getattr(element, "proto", None), "srcdoc", "")
        if srcdoc and "AGENT (" in srcdoc:  # the heat map, not the legend
            return srcdoc
    raise AssertionError("matrix component not found in the rendered page")


@pytest.fixture(scope="module")
def expected() -> dict[str, int]:
    rows = data_client.get_matrix()["rows"]
    return {
        # `data_roles` carries every role (Not used / Supportive / Upgrade);
        # only "Not used" is marked, so counting the dict would overcount by 103.
        "not_used": sum(1 for r in rows for v in r.get("data_roles", {}).values() if v == "Not used"),
        # `directions` carries every non-positive direction (221 cells:
        # unspecified, negative, equivocal, protective). Only protective gets
        # its own mark, so counting the dict would overcount by 215.
        "protective": sum(1 for r in rows for d in r.get("directions", {}).values() if d == "protective"),
    }


def test_the_page_renders_every_not_used_mark(page, expected):
    html = _rendered_matrix(page)
    assert expected["not_used"] > 0, "no 'Not used' cells — test would be vacuous"
    assert html.count(NOT_USED_MARK) == expected["not_used"], (
        "the page is dropping data_roles before the renderer sees them"
    )


def test_the_page_renders_every_protective_mark(page, expected):
    html = _rendered_matrix(page)
    assert expected["protective"] > 0, "no protective cells — test would be vacuous"
    assert html.count(PROTECTIVE_MARK) == expected["protective"], (
        "the page is dropping directions before the renderer sees them"
    )


def test_protective_cells_are_not_painted_as_ordinary_zeros(page):
    html = _rendered_matrix(page)
    assert "protective (reported to suppress this characteristic)" in html


def test_the_page_does_not_rebuild_rows_by_listing_keys():
    """The adapter must carry unknown fields through, or this recurs.

    Any field added to the matrix payload in future has to reach the renderer
    without someone remembering to widen a literal.
    """
    source = PAGE.read_text(encoding="utf-8")
    assert "to_matrix_row" in source
    assert '"scores": r["scores"]' not in source, "row dict is being rebuilt by hand again"


def test_the_adapter_only_renames(expected):
    row = next(r for r in data_client.get_matrix()["rows"] if r.get("data_roles"))
    adapted = to_matrix_row(row)
    assert adapted["id"] == row["agent_id"]
    assert adapted["name"] == row["agent_name"]
    # Everything else survives, including keys this test does not know about.
    for key, value in row.items():
        assert adapted[key] == value, f"{key} was altered by the adapter"


def test_matrix_payload_and_csv_carry_source_count():
    """Score 4 collapses 3- and 4-source vol100 cells; source_count keeps them distinct."""
    rows = data_client.get_matrix()["rows"]
    with_counts = [r for r in rows if r.get("source_counts")]
    assert with_counts, "no source_counts on matrix rows"
    total = sum(len(r["source_counts"]) for r in with_counts)
    assert total > 0
    # At least one score-4 cell keeps a count of 3 (the non-lossy case).
    found_three = any(
        r["scores"].get(kid) == 4 and count == 3 for r in with_counts for kid, count in r["source_counts"].items()
    )
    assert found_three, "vol100 score-4 / source_count=3 pair missing from the matrix payload"

    source = PAGE.read_text(encoding="utf-8")
    assert "source_count" in source, "matrix CSV must export source_count"
    assert "iarc_data_role" in source, "matrix CSV must export iarc_data_role"


def test_the_adapter_preserves_a_field_nobody_has_added_yet():
    """Guards the mechanism rather than today's field list."""
    row = {"agent_id": "a", "agent_name": "A", "scores": {}, "future_field": ["x"]}
    assert to_matrix_row(row)["future_field"] == ["x"]


def test_rendering_through_the_adapter_matches_the_page(page, expected):
    """Ties the component-level check to the page's real input."""
    rows = data_client.get_matrix()["rows"]
    html = matrix_heatmap_html(data_client.list_kccs(), [to_matrix_row(r) for r in rows])
    assert html.count(NOT_USED_MARK) == expected["not_used"]
    assert html.count(PROTECTIVE_MARK) == expected["protective"]


def test_the_csv_export_carries_the_interpretive_fields():
    source = PAGE.read_text(encoding="utf-8")
    for field in ('"direction"', '"source_track"', '"iarc_data_role"'):
        assert field in source, f"{field} missing from the matrix CSV export"


def test_the_page_marks_every_label_outrun_cell():
    """Cells whose score rests on a label the primary systems contradict.

    Only ``protective`` had special rendering, so 53 cells scoring >= 2 with a
    negative / equivocal / unspecified primary direction painted on the positive
    heat ramp exactly like corroborated evidence. 1,1,1-Trichloroethane shows 7
    substantial characteristics of which only 3 are positive-direction.
    """
    from hkcc.app.utils.evidence import DIRECTION_MARKS

    rows = data_client.get_matrix()["rows"]
    html = matrix_heatmap_html(data_client.list_kccs(), [to_matrix_row(r) for r in rows])
    for direction, (glyph, _) in DIRECTION_MARKS.items():
        expected = sum(
            1 for r in rows for kid, d in r.get("directions", {}).items() if d == direction and kid in r["scores"]
        )
        assert expected > 0, f"no {direction} cells — test would be vacuous"
        assert html.count(glyph) >= expected, f"{direction} cells are unmarked"
    assert html.count("primary systems:") == sum(
        1 for r in rows for kid, d in r.get("directions", {}).items() if d in DIRECTION_MARKS and kid in r["scores"]
    )


def test_the_trichloroethane_case_is_visibly_qualified():
    """The reviewer's worked example: 7 substantial, only 3 positive-direction."""
    rows = data_client.get_matrix()["rows"]
    row = next(r for r in rows if r["agent_id"] == "1-1-1-trichloroethane")
    substantial = [k for k, v in row["scores"].items() if v >= 3]
    qualified = [k for k in substantial if row.get("directions", {}).get(k, "positive") != "positive"]
    assert len(substantial) == 7
    assert len(qualified) == 4, "the example no longer exercises the label-outrun case"

    html = matrix_heatmap_html(data_client.list_kccs(), [to_matrix_row(row)])
    assert html.count("primary systems:") == len(
        [k for k, d in row.get("directions", {}).items() if d != "positive" and k in row["scores"]]
    )
