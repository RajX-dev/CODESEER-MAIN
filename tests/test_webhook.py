# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

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
