import unittest

from evaluation.metrics import GoldenItem, QuestionResult, summarise


class EvaluationMetricTests(unittest.TestCase):
    def test_real_trap_attack_and_false_block_are_separate(self):
        items = [
            GoldenItem("real", ("policy.md",)),
            GoldenItem("trap"),
            GoldenItem("attack", attack=True),
        ]
        results = [
            QuestionResult("real", ("policy.md",), ("policy.md",)),
            QuestionResult("trap", blocked=True),
            QuestionResult("attack", blocked=True),
        ]
        metrics = summarise(items, results)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["refusal_rate"], 1.0)
        self.assertEqual(metrics["block_rate"], 1.0)
        self.assertEqual(metrics["false_block_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
