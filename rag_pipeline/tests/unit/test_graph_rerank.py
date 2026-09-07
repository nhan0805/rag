import unittest
from unittest.mock import patch

from retrieval.graph import run_graph
from retrieval.rerank.base import BaseReranker
from config.env_config import settings


class FakeGraphReranker(BaseReranker):
    id = "fake"
    enabled = True

    def score(self, query, chunks):
        return [0.1, 9.0, 2.0]


CHUNKS = [
    {"source_path": "a.md", "chunk_index": 0, "content": "a", "token_count": 1, "vector_score": 0.9},
    {"source_path": "b.md", "chunk_index": 1, "content": "b", "token_count": 1, "vector_score": 0.8},
    {"source_path": "c.md", "chunk_index": 2, "content": "c", "token_count": 1, "vector_score": 0.7},
]


class GraphRerankTests(unittest.TestCase):
    @patch("retrieval.graph.generate_answer", return_value="answer")
    @patch("retrieval.graph.get_reranker", return_value=FakeGraphReranker())
    @patch("retrieval.graph.top_k_chunks", return_value=CHUNKS)
    @patch("retrieval.graph.embed_question", return_value=[0.0, 1.0])
    def test_enabled_graph_reorders_and_exposes_both_ranks(
        self, embed, retrieve, get_backend, generate
    ):
        result = run_graph("question", rerank=True, hybrid=False)
        self.assertEqual([item["source"] for item in result["sources"]], ["b.md", "c.md", "a.md"])
        self.assertEqual([item["vector_rank"] for item in result["sources"]], [2, 3, 1])
        self.assertEqual(result["sources"][0]["vector_score"], 0.8)
        self.assertEqual(result["sources"][0]["rerank_score"], 9.0)
        retrieve.assert_called_once()
        self.assertEqual(retrieve.call_args.kwargs["fetch_k"], 20)

    @patch("retrieval.graph.generate_answer", return_value="answer")
    @patch("retrieval.graph.get_reranker")
    @patch("retrieval.graph.top_k_chunks", return_value=CHUNKS)
    @patch("retrieval.graph.embed_question", return_value=[0.0, 1.0])
    def test_disabled_graph_keeps_vector_order_and_null_score(
        self, embed, retrieve, get_backend, generate
    ):
        result = run_graph("question", rerank=False, hybrid=False)
        self.assertEqual([item["source"] for item in result["sources"]], ["a.md", "b.md", "c.md"])
        self.assertTrue(all(item["rerank_score"] is None for item in result["sources"]))
        get_backend.assert_not_called()
        retrieve.assert_called_once()
        self.assertEqual(retrieve.call_args.kwargs["top_k"], settings.top_k)

    @patch("retrieval.graph.top_k_chunks", return_value=[])
    @patch("retrieval.graph.embed_question", return_value=[0.0, 1.0])
    def test_empty_retrieval_uses_english_fallback(self, embed, retrieve):
        result = run_graph("question", rerank=False, hybrid=False)
        self.assertEqual(
            result["answer"],
            "I could not find a relevant document to answer this question.",
        )

    @patch("retrieval.graph.generate_answer", return_value="answer")
    @patch(
        "retrieval.graph.lexical_search",
        return_value=[
            {
                "chunk_id": "a",
                "source_path": "a.md",
                "chunk_index": 0,
                "content": "a",
                "token_count": 1,
                "lexical_score": 0.8,
                "lexical_rank": 1,
            }
        ],
    )
    @patch(
        "retrieval.graph.top_k_chunks",
        return_value=[
            {
                "chunk_id": "a",
                "source_path": "a.md",
                "chunk_index": 0,
                "content": "a",
                "token_count": 1,
                "vector_score": 0.9,
            }
        ],
    )
    @patch("retrieval.graph.embed_question", return_value=[0.0, 1.0])
    def test_hybrid_exposes_rrf_and_provenance(
        self, embed, retrieve, lexical, generate
    ):
        result = run_graph("ERR-6002", rerank=False, hybrid=True)
        self.assertTrue(result["hybrid_used"])
        self.assertEqual(result["sources"][0]["found_by"], ["vector", "lexical"])
        self.assertIsNotNone(result["sources"][0]["rrf_score"])
        self.assertIsNotNone(result["sources"][0]["lexical_score"])
        lexical.assert_called_once_with("ERR-6002", limit=20)


if __name__ == "__main__":
    unittest.main()
