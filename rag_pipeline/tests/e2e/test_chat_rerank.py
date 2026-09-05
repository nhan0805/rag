import json
import os
import unittest
from urllib.request import Request, urlopen


@unittest.skipUnless(
    os.getenv("RUN_RAG_E2E") == "1",
    "Set RUN_RAG_E2E=1 when the Docker stack is running",
)
class ChatRerankE2ETests(unittest.TestCase):
    base_url = os.getenv("RAG_EVAL_URL", "http://localhost:8000")

    def post_chat(self, rerank):
        body = json.dumps(
            {"question": "Corrector agent để làm gì?", "rerank": rerank}
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

    def test_rerank_contract_on_and_off(self):
        off = self.post_chat(False)
        on = self.post_chat(True)
        self.assertLessEqual(len(off["sources"]), 4)
        self.assertLessEqual(len(on["sources"]), 4)
        self.assertTrue(all(item["rerank_score"] is None for item in off["sources"]))
        self.assertTrue(all(item["rerank_score"] is not None for item in on["sources"]))
        self.assertTrue(all(item["vector_rank"] is not None for item in on["sources"]))


if __name__ == "__main__":
    unittest.main()

