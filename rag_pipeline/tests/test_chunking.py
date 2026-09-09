import unittest

from indexing.step3_chunking_strategy import chunk_text, fixed_token_chunks
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

    def test_qa_aware_chunks_repeat_heading_and_title(self):
        text = "Preamble\n\n## Q1: First\nAnswer one\n\n## Q2: Second\nAnswer two"
        chunks = chunk_text(text, chunk_size=20, overlap=2, title="Lab notes", qa_aware=True)
        self.assertEqual(len(chunks), 2)
        self.assertIn("Lab notes", chunks[0]["content"])
        self.assertIn("## Q1: First", chunks[0]["content"])
        self.assertIn("## Q2: Second", chunks[1]["content"])
        self.assertNotIn("## Q2: Second", chunks[0]["content"])

    def test_qa_aware_flag_off_keeps_fixed_chunking(self):
        text = "## Q1: First\none two three\n\n## Q2: Second\nfour five six"
        chunks = chunk_text(text, chunk_size=4, overlap=1, qa_aware=False)
        self.assertEqual(chunks[0]["content"], "## Q1: First one")


if __name__ == "__main__":
    unittest.main()
