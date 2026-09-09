import unittest

from pydantic import ValidationError

from api.routes_auth import SetRoleRequest


class AuthRouteModelTests(unittest.TestCase):
    def test_set_role_normalizes_supported_role(self):
        self.assertEqual(SetRoleRequest(role=" MANAGER ").role, "manager")

    def test_set_role_rejects_admin_from_role_management_ui(self):
        with self.assertRaises(ValidationError):
            SetRoleRequest(role="admin")


if __name__ == "__main__":
    unittest.main()
