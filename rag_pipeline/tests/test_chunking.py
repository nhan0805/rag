import unittest

from indexing.step3_chunking_strategy import fixed_token_chunks
from indexing.step4_preprocessing import clean_text


class ChunkingTests(unittest.TestCase):
    def test_fixed_token_windows_overlap(self):
        chunks = fixed_token_chunks("one two three four five six seven eight nine ten", 4, 1)
        self.assertEqual([chunk["chunk_index"] for chunk in chunks], [0, 1, 2])
        self.assertEqual(chunks[0]["content"], "one two three four")
        self.assertEqual(chunks[1]["content"], "four five six seven")
        self.assertEqual(chunks[-1]["content"], "seven eight nine ten")

    def test_invalid_overlap(self):
        with self.assertRaises(ValueError):
            fixed_token_chunks("text", 4, 4)

    def test_clean_text(self):
        self.assertEqual(clean_text("  hello\t world\n\n\nthere  "), "hello world\n\nthere")


if __name__ == "__main__":
    unittest.main()
