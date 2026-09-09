import hashlib
import unittest

from indexing.index_runner import content_sha256


class IndexHashTests(unittest.TestCase):
    def test_hash_is_utf8_sha256(self):
        text = "Xin chào RAG — bản mới"
        self.assertEqual(content_sha256(text), hashlib.sha256(text.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    unittest.main()
