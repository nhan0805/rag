import copy
import unittest

from retrieval.hybrid.fusion import reciprocal_rank_fusion


class HybridFusionTests(unittest.TestCase):
    def test_rrf_formula_and_field_union(self):
        vector = [
            {
                "chunk_id": "a",
                "source_path": "same.md",
                "vector_score": 0.9,
                "vector_rank": 1,
            },
            {
                "chunk_id": "b",
                "source_path": "same.md",
                "vector_score": 0.8,
                "vector_rank": 2,
            },
        ]
        lexical = [
            {
                "chunk_id": "b",
                "source_path": "same.md",
                "lexical_score": 0.4,
                "lexical_rank": 2,
            },
            {
                "chunk_id": "c",
                "source_path": "same.md",
                "lexical_score": 0.3,
                "lexical_rank": 2,
            },
        ]
        original = copy.deepcopy([vector, lexical])

        result = reciprocal_rank_fusion(
            {"vector": vector, "lexical": lexical}, k=60
        )
        by_id = {item["chunk_id"]: item for item in result}

        self.assertAlmostEqual(by_id["b"]["rrf_score"], 1 / 62 + 1 / 61)
        self.assertEqual(by_id["b"]["found_by"], ["vector", "lexical"])
        self.assertEqual(by_id["b"]["vector_score"], 0.8)
        self.assertEqual(by_id["b"]["lexical_score"], 0.4)
        self.assertEqual([item["chunk_id"] for item in result], ["b", "a", "c"])
        self.assertEqual([vector, lexical], original)

    def test_consensus_at_rank_two_beats_single_rank_one(self):
        result = reciprocal_rank_fusion(
            [
                [
                    {"chunk_id": "top", "vector_score": 1.0},
                    {"chunk_id": "consensus", "vector_score": 0.9},
                ],
                [
                    {"chunk_id": "other", "lexical_score": 1.0},
                    {"chunk_id": "consensus", "lexical_score": 0.8},
                ],
            ],
            k=60,
        )
        self.assertEqual(result[0]["chunk_id"], "consensus")

    def test_empty_lists_and_same_file_different_chunks(self):
        result = reciprocal_rank_fusion(
            {"vector": [], "lexical": [{"chunk_id": "x", "source_path": "a.md"}]}
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["rrf_rank"], 1)


if __name__ == "__main__":
    unittest.main()
