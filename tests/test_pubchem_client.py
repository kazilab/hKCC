

def test_assay_summary_table_parsing():
    data = {
        "Table": {
            "Columns": {"Column": ["AID", "Outcome", "Description"]},
            "Row": [
                {"Cell": ["1", "Active", "Test assay A"]},
                {"Cell": ["2", "Inactive", "Test assay B"]},
            ],
        }
    }
    # Simulate parsing logic inline (same as function expects full API response)
    from hkcc.pipelines.clients import pubchem as pc

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return data

    def fake_get_json(url: str, **kwargs):
        return data

    orig = pc._get_json
    pc._get_json = fake_get_json  # type: ignore[method-assign]
    try:
        cols, rows = pc.assay_summary_table(999, max_rows=10)
        assert cols == ["AID", "Outcome", "Description"]
        assert rows[0]["AID"] == "1"
        assert rows[1]["Outcome"] == "Inactive"
    finally:
        pc._get_json = orig  # type: ignore[method-assign]
