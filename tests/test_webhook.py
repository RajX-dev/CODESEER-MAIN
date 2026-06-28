# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from n3mo.api.webhook_handler import app

client = TestClient(app)

def test_webhook_disabled_locally():
    with patch.dict(os.environ, {"N3MO_SAAS_MODE": "false"}):
        resp = client.post(
            "/webhook",
            json={"action": "opened"},
            headers={"X-GitHub-Event": "pull_request"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "error"
        assert "SaaS-exclusive feature" in data.get("message")

def test_webhook_signature_required():
    with patch("n3mo.api.webhook_handler.GITHUB_WEBHOOK_SECRET", "my_secret"), \
         patch.dict(os.environ, {"N3MO_SAAS_MODE": "true"}):
         
        # Without signature, should be 401
        resp = client.post("/webhook", json={"action": "opened"}, headers={"X-GitHub-Event": "pull_request"})
        assert resp.status_code == 401

        # With bad signature, should be 401
        resp = client.post(
            "/webhook",
            json={"action": "opened"},
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": "sha256=invalid_hash"
            }
        )
        assert resp.status_code == 401

        # With correct signature, should proceed
        payload = {"action": "opened"}
        payload_bytes = json.dumps(payload).encode()
        correct_hash = hmac.new(b"my_secret", payload_bytes, hashlib.sha256).hexdigest()
        
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = MagicMock()
            with patch.dict(os.environ, {"GITHUB_PAT": "mock_pat"}):
                resp = client.post(
                    "/webhook",
                    content=payload_bytes,
                    headers={
                        "X-GitHub-Event": "pull_request",
                        "Content-Type": "application/json",
                        "X-Hub-Signature-256": f"sha256={correct_hash}"
                    }
                )
            assert resp.status_code == 200
            mock_urlopen.assert_called_once()

def test_webhook_ignores_other_events():
    with patch("n3mo.api.webhook_handler.GITHUB_WEBHOOK_SECRET", "my_secret"), \
         patch.dict(os.environ, {"N3MO_SAAS_MODE": "true"}):
         
        payload = {"action": "created"}
        payload_bytes = json.dumps(payload).encode()
        correct_hash = hmac.new(b"my_secret", payload_bytes, hashlib.sha256).hexdigest()
        
        resp = client.post(
            "/webhook",
            content=payload_bytes,
            headers={
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={correct_hash}"
            }
        )
        assert resp.status_code == 200
        assert "ignored" in resp.json().get("message")
