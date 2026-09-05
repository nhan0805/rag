import unittest

from shared.md_frontmatter import split_frontmatter


class FrontmatterTests(unittest.TestCase):
    def test_split_frontmatter(self):
        parsed = split_frontmatter("---\ntitle: Demo\nstatus: done\n---\n\n# Body")
        self.assertEqual(parsed.frontmatter, "title: Demo\nstatus: done")
        self.assertEqual(parsed.body, "# Body")

    def test_plain_markdown_is_untouched(self):
        parsed = split_frontmatter("# Heading\n\nContent")
        self.assertEqual(parsed.frontmatter, "")
        self.assertEqual(parsed.body, "# Heading\n\nContent")


if __name__ == "__main__":
    unittest.main()
