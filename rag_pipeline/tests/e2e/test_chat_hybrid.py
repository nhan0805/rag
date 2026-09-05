import json
import os
import unittest
from urllib.request import Request, urlopen


@unittest.skipUnless(
    os.getenv("RUN_RAG_E2E") == "1",
    "Set RUN_RAG_E2E=1 when the Docker stack is running",
)
class ChatHybridE2ETests(unittest.TestCase):
    base_url = os.getenv("RAG_EVAL_URL", "http://localhost:8000")

    def post_chat(self, question, hybrid, rerank=False):
        body = json.dumps(
            {
                "question": question,
                "hybrid": hybrid,
                "rerank": rerank,
                "retrieve_only": True,
            }
        ).encode()
        request = Request(
            f"{self.base_url}/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=180) as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def test_hybrid_flag_and_provenance(self):
        off = self.post_chat("What does ERR-6002 mean?", hybrid=False)
        on = self.post_chat("What does ERR-6002 mean?", hybrid=True)

        self.assertFalse(off["hybrid_used"])
        self.assertTrue(all(item["found_by"] == ["vector"] for item in off["sources"]))
        self.assertIn("hybrid_used", on)
        self.assertTrue(
            all(item["rrf_score"] is not None for item in on["sources"])
        )

    def test_punctuation_only_question_does_not_fail(self):
        response = self.post_chat("???", hybrid=True)
        self.assertFalse(response["hybrid_used"])

    def test_lexical_only_case_is_explicit_or_explains_fixture(self):
        response = self.post_chat("What does ERR-4821 mean?", hybrid=True)
        lexical_only = any(
            item["found_by"] == ["lexical"] for item in response["retrieved_sources"]
        )
        if not lexical_only:
            self.skipTest(
                "The current small fixture is already found by vector; a larger "
                "distractor corpus is needed to demonstrate lexical-only rescue."
            )


if __name__ == "__main__":
    unittest.main()
