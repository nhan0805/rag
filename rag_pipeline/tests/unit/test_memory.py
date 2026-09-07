import unittest

from memory.contextualise import contextualise


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


if __name__ == "__main__":
    unittest.main()
