import unittest
from types import SimpleNamespace
from unittest.mock import patch

from memory.contextualise import contextualise
from memory.store import log_memory_event


class MemoryContextTests(unittest.TestCase):
    def test_first_turn_is_returned_verbatim(self):
        question = "  What is the leave policy?  "
        self.assertEqual(contextualise(question, []), question)

    def test_independent_question_is_not_rewritten(self):
        question = "What is the sick leave policy?"
        self.assertEqual(contextualise(question, [{"question": "Earlier?"}]), question)

    def test_dependent_follow_up_includes_previous_topic(self):
        result = contextualise(
            "Thế còn nghỉ ốm?",
            [{"question": "Nhân viên mới được bao nhiêu ngày phép năm?"}],
        )
        self.assertIn("phép năm", result)
        self.assertIn("nghỉ ốm", result)

    @patch("memory.store.memory_file_logger.info")
    def test_memory_telemetry_hashes_identifiers(self, info):
        log_memory_event(
            "write",
            "conversation-with-sensitive-name",
            "user-with-sensitive-name",
            question_chars=12,
            answer_chars=20,
        )
        message = str(info.call_args)
        self.assertIn("memory_%s %s", message)
        self.assertIn("write", message)
        self.assertNotIn("conversation-with-sensitive-name", message)
        self.assertNotIn("user-with-sensitive-name", message)
        self.assertIn("question_chars=12", message)

    @patch("memory.store.memory_file_logger.info")
    def test_memory_question_content_is_opt_in(self, info):
        with patch(
            "memory.store.settings",
            SimpleNamespace(memory_log_question=True),
        ):
            log_memory_event(
                "context",
                "conversation",
                "user",
                input_question="Còn điều kiện?",
                contextualized_question="Chính sách nghỉ phép. Additional question about điều kiện?",
            )
        message = str(info.call_args)
        self.assertIn("Còn điều kiện?", message)
        self.assertIn("contextualized_question", message)


if __name__ == "__main__":
    unittest.main()
