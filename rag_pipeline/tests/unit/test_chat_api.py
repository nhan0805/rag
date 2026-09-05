import unittest
from unittest.mock import patch

from api.routes_chat import ChatRequest, chat


class ChatApiTests(unittest.TestCase):
    @patch(
        "api.routes_chat.answer_question",
        return_value={
            "answer": "answer",
            "sources": [],
            "retrieved_sources": [],
            "hybrid_used": False,
        },
    )
    def test_hybrid_flag_is_forwarded_to_runner(self, answer_question):
        response = chat(
            ChatRequest(question="question", hybrid=False, rerank=True)
        )
        answer_question.assert_called_once_with(
            "question", rerank=True, hybrid=False, retrieve_only=False
        )
        self.assertFalse(response.hybrid_used)


if __name__ == "__main__":
    unittest.main()
