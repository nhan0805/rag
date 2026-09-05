import unittest

from retrieval.graph import _rerank_node
from retrieval.rerank import get_reranker


class RerankRegistryTests(unittest.TestCase):
    def test_invalid_backend_fails_loudly(self):
        with self.assertRaisesRegex(ValueError, "RERANK_BACKEND"):
            get_reranker("not-a-backend")

    def test_none_backend_is_explicitly_disabled(self):
        self.assertIsNone(get_reranker("none"))

    def test_disabled_node_keeps_vector_order_and_null_score(self):
        state = {
            "question": "hello",
            "rerank": False,
            "candidate_chunks": [
                {"source_path": "a.md", "chunk_index": 0, "content": "a", "vector_rank": 1, "vector_score": 0.8},
                {"source_path": "b.md", "chunk_index": 1, "content": "b", "vector_rank": 2, "vector_score": 0.7},
            ],
        }
        _rerank_node(state)
        self.assertEqual([item["source_path"] for item in state["chunks"]], ["a.md", "b.md"])
        self.assertTrue(all(item["rerank_score"] is None for item in state["chunks"]))


if __name__ == "__main__":
    unittest.main()

