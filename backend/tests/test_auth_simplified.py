import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
_RAG_DIR = os.path.join(_BACKEND_DIR, "rag")
_REPO_DIR = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_RAG_DIR, _BACKEND_DIR, _REPO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rag.app import create_app
from modules.auth.constants import RegistryType


class TestSimplifiedAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # -------------------------------------------------------------------------
    # 1. /auth/check - Register and Login checks
    # -------------------------------------------------------------------------

    @patch("modules.auth.services._find_in_registry")
    def test_check_register_user_not_found(self, mock_find):
        mock_find.return_value = (None, None)
        res = self.client.post(
            "/auth/check",
            json={"email": "unknown@university.edu", "action": "register", "role": "student"},
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Either user doesn't exist or already registered.")

    @patch("modules.auth.services._find_in_registry")
    def test_check_login_user_not_found(self, mock_find):
        mock_find.return_value = (None, None)
        res = self.client.post(
            "/auth/check",
            json={"email": "unknown@university.edu", "action": "login", "role": "student"},
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Account is not registered. Please register.")

    @patch("modules.auth.services._find_in_registry")
    @patch("modules.auth.services._get_auth_user_by_email")
    def test_check_register_eligible(self, mock_auth_user, mock_find):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": None,
            },
            RegistryType.STUDENT,
        )
        mock_auth_user.return_value = None

        res = self.client.post(
            "/auth/check",
            json={"email": "jane@university.edu", "action": "register", "role": "student"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "eligible")
        self.assertEqual(data.get("name"), "Jane Doe")
        self.assertEqual(data.get("email"), "jane@university.edu")
        self.assertIn("registration_token", data)

    @patch("modules.auth.services._find_in_registry")
    def test_check_register_already_registered(self, mock_find):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": "profile-uuid-456",
            },
            RegistryType.STUDENT,
        )

        res = self.client.post(
            "/auth/check",
            json={"email": "jane@university.edu", "action": "register", "role": "student"},
        )
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Either user doesn't exist or already registered.")

    @patch("modules.auth.services._find_in_registry")
    def test_check_login_registered(self, mock_find):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": "profile-uuid-456",
            },
            RegistryType.STUDENT,
        )

        res = self.client.post(
            "/auth/check",
            json={"email": "jane@university.edu", "action": "login", "role": "student"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "registered")
        self.assertEqual(data.get("name"), "Jane Doe")
        self.assertEqual(data.get("email"), "jane@university.edu")

    @patch("modules.auth.services._find_in_registry")
    @patch("modules.auth.services._get_auth_user_by_email")
    def test_check_login_unregistered(self, mock_auth_user, mock_find):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": None,
            },
            RegistryType.STUDENT,
        )
        mock_auth_user.return_value = None

        res = self.client.post(
            "/auth/check",
            json={"email": "jane@university.edu", "action": "login", "role": "student"},
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Account is not registered. Please register.")

    # -------------------------------------------------------------------------
    # 2. /auth/register - Password validation and Confirmation Mail
    # -------------------------------------------------------------------------

    def test_register_short_password(self):
        res = self.client.post(
            "/auth/register",
            json={
                "email": "jane@university.edu",
                "password": "short",
                "confirm_password": "short",
            },
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("at least 8 characters", data.get("error", ""))

    def test_register_mismatched_password(self):
        res = self.client.post(
            "/auth/register",
            json={
                "email": "jane@university.edu",
                "password": "Password123",
                "confirm_password": "Password456",
            },
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("do not match", data.get("error", ""))

    @patch("modules.auth.services._find_in_registry")
    @patch("modules.auth.services._get_auth_user_by_email")
    @patch("modules.auth.services.get_supabase_client")
    @patch("modules.auth.services.get_supabase_admin_client")
    def test_register_success_sends_confirmation_email(
        self, mock_admin, mock_client, mock_auth_user, mock_find
    ):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": None,
            },
            RegistryType.STUDENT,
        )
        mock_auth_user.return_value = None

        # Supabase sign_up mock
        mock_user = MagicMock()
        mock_user.id = "new-user-uuid"
        mock_user.identities = [MagicMock()]
        mock_signup_resp = MagicMock()
        mock_signup_resp.user = mock_user
        mock_client.return_value.auth.sign_up.return_value = mock_signup_resp

        # Supabase RPC mock
        mock_rpc = MagicMock()
        mock_admin.return_value.rpc.return_value = mock_rpc
        mock_rpc.execute.return_value = None

        res = self.client.post(
            "/auth/register",
            json={
                "email": "jane@university.edu",
                "role": "student",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data.get("status"), "pending_confirmation")
        self.assertIn("confirmation email has been sent", data.get("message", ""))
        self.assertEqual(data.get("email"), "jane@university.edu")

        # Verify client.auth.sign_up was invoked (dispatches Supabase confirmation mail)
        mock_client.return_value.auth.sign_up.assert_called_once()
        call_args = mock_client.return_value.auth.sign_up.call_args[0][0]
        self.assertEqual(call_args["email"], "jane@university.edu")
        self.assertEqual(call_args["password"], "Password123!")

    # -------------------------------------------------------------------------
    # 3. /auth/login - Registry check & Confirmation requirement
    # -------------------------------------------------------------------------

    @patch("modules.auth.services._find_in_registry")
    @patch("modules.auth.services._get_auth_user_by_email")
    def test_login_unregistered_email_reports_error(self, mock_auth_user, mock_find):
        mock_find.return_value = (None, None)
        mock_auth_user.return_value = None

        res = self.client.post(
            "/auth/login",
            json={"email": "notregistered@university.edu", "password": "Password123!"},
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Account is not registered. Please register.")

    @patch("modules.auth.services._find_in_registry")
    @patch("modules.auth.services.get_supabase_client")
    def test_login_unconfirmed_email_blocked(self, mock_client, mock_find):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": "profile-uuid",
            },
            RegistryType.STUDENT,
        )

        mock_client.return_value.auth.sign_in_with_password.side_effect = Exception("Email not confirmed")

        res = self.client.post(
            "/auth/login",
            json={"email": "jane@university.edu", "password": "Password123!"},
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn("Please confirm your email before signing in", data.get("error", ""))

    @patch("modules.auth.services._find_in_registry")
    @patch("modules.auth.services.get_supabase_client")
    def test_login_success_confirmed(self, mock_client, mock_find):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": "profile-uuid",
            },
            RegistryType.STUDENT,
        )

        mock_session = MagicMock()
        mock_session.access_token = "valid-token-abc"
        mock_session.refresh_token = "refresh-token-xyz"
        mock_session.expires_at = 1234567890
        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        mock_user.email = "jane@university.edu"

        mock_resp = MagicMock()
        mock_resp.session = mock_session
        mock_resp.user = mock_user
        mock_client.return_value.auth.sign_in_with_password.return_value = mock_resp

        res = self.client.post(
            "/auth/login",
            json={"email": "jane@university.edu", "password": "Password123!"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("access_token"), "valid-token-abc")
        self.assertEqual(data.get("user", {}).get("email"), "jane@university.edu")

    # -------------------------------------------------------------------------
    # 4. /auth/resend-confirmation
    # -------------------------------------------------------------------------

    @patch("modules.auth.services.get_supabase_client")
    def test_resend_confirmation(self, mock_client):
        mock_client.return_value.auth.resend.return_value = None

        res = self.client.post(
            "/auth/resend-confirmation",
            json={"email": "jane@university.edu"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("resent successfully", data.get("message", ""))
        mock_client.return_value.auth.resend.assert_called_once_with(
            {"type": "signup", "email": "jane@university.edu"}
        )

    # -------------------------------------------------------------------------
    # 5. Compatibility routes: /check-student & /check-faculty
    # -------------------------------------------------------------------------

    @patch("modules.auth.services._find_in_registry")
    def test_check_student_compatibility_route(self, mock_find):
        mock_find.return_value = (
            {
                "id": "rec-123",
                "name": "Jane Doe",
                "email": "jane@university.edu",
                "profile_id": "profile-uuid",
            },
            RegistryType.STUDENT,
        )

        res = self.client.post(
            "/auth/check-student",
            json={"email": "jane@university.edu", "action": "login"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "registered")
