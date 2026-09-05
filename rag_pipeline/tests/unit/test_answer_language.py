import unittest

from retrieval.step8_build_prompt import build_prompt
from retrieval.step9_generate_answer import contains_vietnamese


class AnswerLanguageTests(unittest.TestCase):
    def test_prompt_requires_translation_to_english(self):
        prompt = build_prompt("overtime policy?", "Ngày thường: 150%.")
        self.assertIn("MUST be entirely in English", prompt)
        self.assertIn("Translate relevant Vietnamese facts into English", prompt)
        self.assertIn("do not copy Vietnamese sentences", prompt)

    def test_vietnamese_detection(self):
        self.assertTrue(contains_vietnamese("Ngày thường: 150%."))
        self.assertFalse(contains_vietnamese("On regular days: 150%."))


if __name__ == "__main__":
    unittest.main()
