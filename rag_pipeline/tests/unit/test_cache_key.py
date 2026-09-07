import unittest

from retrieval.cache.key import scope_key


class CacheKeyTests(unittest.TestCase):
    def test_permission_order_and_duplicates_do_not_change_key(self):
        self.assertEqual(
            scope_key(["B", "A", "A"], True, False),
            scope_key(["A", "B"], True, False),
        )

    def test_subset_and_configuration_have_distinct_keys(self):
        self.assertNotEqual(scope_key(["A"], True, False), scope_key(["A", "B"], True, False))
        self.assertNotEqual(scope_key(["A"], True, False), scope_key(["A"], False, False))
        self.assertNotEqual(scope_key(["A"], True, False), scope_key(["A"], True, True))


if __name__ == "__main__":
    unittest.main()
