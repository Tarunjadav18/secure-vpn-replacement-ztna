import os
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ["ZTNA_ADMIN_PASSWORD"] = "test-password"
from src.ztna.app import app, TOKENS


class ZtnaGatewayTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        TOKENS.clear()

    def login(self):
        return self.client.post("/login", json={"username": "admin", "password": "test-password"})

    def test_homepage_serves_demo_ui(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ZTNA Access Gateway", response.data)

    def test_health_is_available(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_login_rejects_bad_credentials(self):
        self.assertEqual(self.client.post("/login", json={"username": "admin", "password": "wrong"}).status_code, 401)

    def test_failed_login_emits_structured_audit_event(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            with patch("src.ztna.app.AUDIT_LOG", audit_path):
                response = self.client.post("/login", json={"username": "admin", "password": "wrong"})
            self.assertEqual(response.status_code, 401)
            event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(event["event"], "login_denied")
            self.assertEqual(event["user"], "admin")
            self.assertIn("source_ip", event)

    def test_app_requires_authentication(self):
        self.assertEqual(self.client.get("/apps/portal").status_code, 401)

    def test_valid_identity_still_needs_device_posture(self):
        token = self.login().get_json()["access_token"]
        response = self.client.get("/apps/portal", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 403)

    def test_trusted_device_receives_app_specific_access(self):
        token = self.login().get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Device-Managed": "true", "X-Device-Compliant": "true"}
        self.assertEqual(self.client.get("/apps/portal", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/apps/admin", headers=headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()
