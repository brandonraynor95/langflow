from lfx.components.datastax.astradb_vectorstore import AstraDBVectorStoreComponent


class TestAstraDBVectorStoreComponent:
    def test_sanitize_metadata_replaces_non_finite_floats(self):
        metadata = {
            "score": float("nan"),
            "nested": {"upper": float("inf"), "lower": float("-inf")},
            "items": [1.0, float("nan"), {"v": float("inf")}],
        }

        sanitized = AstraDBVectorStoreComponent._sanitize_metadata(metadata)

        assert sanitized["score"] is None
        assert sanitized["nested"]["upper"] is None
        assert sanitized["nested"]["lower"] is None
        assert sanitized["items"][1] is None
        assert sanitized["items"][2]["v"] is None
