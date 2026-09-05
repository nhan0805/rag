import unittest
from unittest.mock import patch

from retrieval.rerank.llm_reranker import LLMReranker, _parse_scores


CHUNKS = [
    {"content": "first", "vector_score": 0.8},
    {"content": "second", "vector_score": 0.6},
]


class LLMRerankerTests(unittest.TestCase):
    def test_parse_json_scores(self):
        self.assertEqual(_parse_scores('[{"index":0,"score":2},{"index":1,"score":8}]', 2), [2.0, 8.0])
        self.assertEqual(_parse_scores("```json\n[1, 3]\n```", 2), [1.0, 3.0])

    def test_malformed_response_falls_back_to_vector_order(self):
        with patch("retrieval.rerank.llm_reranker.generate_answer", return_value="not json"):
            self.assertEqual(LLMReranker().score("q", CHUNKS), [0.8, 0.6])

    def test_valid_response_is_returned_in_input_order(self):
        with patch(
            "retrieval.rerank.llm_reranker.generate_answer",
            return_value='[{"index":0,"score":2},{"index":1,"score":8}]',
        ):
            self.assertEqual(LLMReranker().score("q", CHUNKS), [2.0, 8.0])


if __name__ == "__main__":
    unittest.main()

