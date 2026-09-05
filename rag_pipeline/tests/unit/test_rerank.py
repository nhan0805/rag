import unittest

from retrieval.rerank.base import BaseReranker, apply_rerank


class FakeReranker(BaseReranker):
    id = "fake"
    enabled = True

    def __init__(self, scores):
        self.scores = scores

    def score(self, query, chunks):
        self.query = query
        self.chunk_count = len(chunks)
        return self.scores


def make_chunks():
    return [
        {"source_path": "a.md", "chunk_index": 0, "content": "a", "vector_score": 0.91},
        {"source_path": "b.md", "chunk_index": 1, "content": "b", "vector_score": 0.72},
        {"source_path": "c.md", "chunk_index": 2, "content": "c", "vector_score": 0.61},
    ]


class RerankPolicyTests(unittest.TestCase):
    def test_scores_sort_and_top_n(self):
        result = apply_rerank(
            "query", make_chunks(), FakeReranker([0.2, 9.5, 4.0]), top_n=2
        )
        self.assertEqual([item["source_path"] for item in result], ["b.md", "c.md"])
        self.assertEqual([item["vector_rank"] for item in result], [2, 3])
        self.assertEqual([item["rerank_score"] for item in result], [9.5, 4.0])
        self.assertEqual(result[0]["vector_score"], 0.72)

    def test_min_score_filters_but_keeps_one_fallback(self):
        result = apply_rerank(
            "query", make_chunks(), FakeReranker([-2.0, -1.0, -3.0]), top_n=4, min_score=0.0
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_path"], "b.md")

    def test_empty_input_and_score_contract(self):
        backend = FakeReranker([])
        self.assertEqual(apply_rerank("query", [], backend, top_n=2), [])
        with self.assertRaises(ValueError):
            apply_rerank("query", make_chunks(), FakeReranker([1.0]), top_n=2)

    def test_existing_vector_rank_is_preserved(self):
        chunks = make_chunks()
        chunks[0]["vector_rank"] = 7
        result = apply_rerank("query", chunks, FakeReranker([3.0, 2.0, 1.0]), top_n=3)
        self.assertEqual(result[0]["vector_rank"], 7)


if __name__ == "__main__":
    unittest.main()

