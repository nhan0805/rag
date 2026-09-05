import unittest

from retrieval.hybrid.query_builder import build_tsquery, extract_terms


class HybridQueryBuilderTests(unittest.TestCase):
    def test_terms_keep_identifiers_and_deduplicate(self):
        terms = extract_terms(
            "How does ERR-6002 compare with HR-114 in fill_and_advance 1.2.3?"
        )
        self.assertEqual(
            terms,
            [
                "err-6002",
                "compare",
                "with",
                "hr-114",
                "in",
                "fill_and_advance",
                "1.2.3",
            ],
        )

    def test_non_kept_separators_become_spaces(self):
        self.assertEqual(extract_terms("fetch_k=20"), ["fetch_k", "20"])
        self.assertNotIn("fetch_k20", extract_terms("fetch_k=20"))

    def test_build_uses_or_and_question_words_are_removed(self):
        query = build_tsquery("What does ERR-6002 mean?")
        self.assertEqual(query, "err-6002 | mean")
        self.assertNotIn("&", query)

    def test_empty_or_punctuation_only_question_is_safe(self):
        self.assertEqual(extract_terms("??? !!!"), [])
        self.assertEqual(build_tsquery("??? !!!"), "")


if __name__ == "__main__":
    unittest.main()
