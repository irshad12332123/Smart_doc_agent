import os
import sys
import unittest
from pathlib import Path

# Ensure backend directory, rag, and project root are on sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
_RAG_DIR = os.path.join(_BACKEND_DIR, "rag")
_REPO_DIR = str(Path(__file__).resolve().parent.parent.parent)
for _p in (_RAG_DIR, _BACKEND_DIR, _REPO_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rag.app import create_app


class TestCORSConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_preflight_vercel_frontend_origin(self):
        res = self.client.open(
            "/auth/login",
            method="OPTIONS",
            headers={"Origin": "https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            res.headers.get("Access-Control-Allow-Origin"),
            "https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app",
        )
        self.assertIn("POST", res.headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("Authorization", res.headers.get("Access-Control-Allow-Headers", ""))
        self.assertEqual(res.headers.get("Access-Control-Allow-Credentials"), "true")

    def test_preflight_vercel_frontend_origin_with_trailing_slash(self):
        res = self.client.open(
            "/auth/login",
            method="OPTIONS",
            headers={"Origin": "https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app/"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            res.headers.get("Access-Control-Allow-Origin"),
            "https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app",
        )

    def test_preflight_render_backend_origin(self):
        res = self.client.open(
            "/api/health",
            method="OPTIONS",
            headers={"Origin": "https://smart-doc-agent-1fcm.onrender.com"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            res.headers.get("Access-Control-Allow-Origin"),
            "https://smart-doc-agent-1fcm.onrender.com",
        )

    def test_preflight_localhost_5173(self):
        res = self.client.open(
            "/auth/login",
            method="OPTIONS",
            headers={"Origin": "http://localhost:5173"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")

    def test_preflight_localhost_dynamic_port(self):
        res = self.client.open(
            "/auth/login",
            method="OPTIONS",
            headers={"Origin": "http://localhost:5174"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "http://localhost:5174")

    def test_preflight_127_0_0_1(self):
        res = self.client.open(
            "/auth/login",
            method="OPTIONS",
            headers={"Origin": "http://127.0.0.1:3000"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:3000")

    def test_preflight_preview_vercel_deployment(self):
        res = self.client.open(
            "/auth/login",
            method="OPTIONS",
            headers={"Origin": "https://smart-doc-agent-preview-123.vercel.app"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            res.headers.get("Access-Control-Allow-Origin"),
            "https://smart-doc-agent-preview-123.vercel.app",
        )

    def test_preflight_unauthorized_origin(self):
        res = self.client.open(
            "/auth/login",
            method="OPTIONS",
            headers={"Origin": "https://attacker-site.com"},
        )
        self.assertEqual(res.status_code, 204)
        self.assertIsNone(res.headers.get("Access-Control-Allow-Origin"))

    def test_get_health_endpoint_cors_headers(self):
        res = self.client.get(
            "/api/health",
            headers={"Origin": "https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("Access-Control-Allow-Origin"),
            "https://smart-doc-agent-git-main-md-irshads-projects-07456f4e.vercel.app",
        )
        self.assertEqual(res.headers.get("Vary"), "Origin")


if __name__ == "__main__":
    unittest.main()
