import unittest
from uuid import uuid4

from auth.security import create_access_token, decode_access_token, hash_password, verify_password


class AuthSecurityTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        encoded = hash_password("local-password-123")
        self.assertTrue(verify_password("local-password-123", encoded))
        self.assertFalse(verify_password("wrong-password", encoded))

    def test_jwt_round_trip(self):
        token = create_access_token(uuid4(), "user@example.local")
        self.assertEqual(decode_access_token(token)["email"], "user@example.local")


if __name__ == "__main__":
    unittest.main()
