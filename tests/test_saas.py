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
import pytest
import jwt
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from n3mo.api_server import app
from n3mo.license_validator import verify_license_key, get_license_hash
from n3mo.api.marketplace import generate_license_jwt

client = TestClient(app)

# Test Cryptographic License Keys
def test_license_validator_fallback_free():
    # No key provided
    res = verify_license_key("")
    assert res["valid"] is False
    assert res["plan_type"] == "free"
    assert res["max_loc"] == 15000

    # No configuration set in environment
    with patch.dict(os.environ, {}, clear=True):
        res = verify_license_key("some_jwt_token")
        assert res["valid"] is False
        assert res["plan_type"] == "free"
        assert "licensing configuration missing" in res["reason"]

def test_license_validator_hs256():
    secret = "my-test-secret"
    with patch.dict(os.environ, {"N3MO_LICENSE_SECRET": secret}, clear=True):
        # 1. Generate token
        token = generate_license_jwt(
            owner_name="TestOrg",
            plan_type="enterprise",
            max_loc=50000,
            duration_days=1
        )
        
        # 2. Verify token
        res = verify_license_key(token)
        assert res["valid"] is True
        assert res["plan_type"] == "enterprise"
        assert res["max_loc"] == 50000
        assert res["owner"] == "TestOrg"

def test_license_validator_expired():
    secret = "my-test-secret"
    with patch.dict(os.environ, {"N3MO_LICENSE_SECRET": secret}, clear=True):
        # Generate an already expired token
        token = generate_license_jwt(
            owner_name="ExpiredOrg",
            plan_type="enterprise",
            max_loc=-1,
            duration_days=-1 # Expired
        )
        
        res = verify_license_key(token)
        assert res["valid"] is False
        assert "expired" in res["reason"].lower()

# Test SaaS Auth Routing Endpoints
def test_saas_auth_login():
    with patch.dict(os.environ, {"GITHUB_CLIENT_ID": "mock_client_id"}):
        resp = client.get("/api/auth/login", follow_redirects=False)
        assert resp.status_code == 307 # Temporary redirect
        assert "github.com/login/oauth/authorize" in resp.headers["location"]
        assert "client_id=mock_client_id" in resp.headers["location"]

@patch("urllib.request.urlopen")
@patch("n3mo.api.auth.upsert_user")
def test_saas_auth_callback(mock_upsert, mock_urlopen):
    # Mock token exchange response
    mock_token_resp = MagicMock()
    mock_token_resp.read.return_value = b'{"access_token": "gh_access_token_123"}'
    
    # Mock user profile response
    mock_profile_resp = MagicMock()
    mock_profile_resp.read.return_value = b'{"id": 9999, "login": "testuser", "email": "test@n3mo.com", "avatar_url": "http://avatar"}'
    
    mock_token_resp.__enter__.return_value = mock_token_resp
    mock_profile_resp.__enter__.return_value = mock_profile_resp
    mock_urlopen.side_effect = [mock_token_resp, mock_profile_resp]
    
    mock_upsert.return_value = {
        "id": "user-uuid-123",
        "github_id": 9999,
        "username": "testuser",
        "email": "test@n3mo.com",
        "avatar_url": "http://avatar",
        "created_at": datetime.now()
    }
    
    with patch.dict(os.environ, {
        "GITHUB_CLIENT_ID": "cid",
        "GITHUB_CLIENT_SECRET": "csec",
        "JWT_SESSION_SECRET": "test_jwt_secret"
    }):
        resp = client.get("/api/auth/callback?code=mock_code", follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == "http://localhost:3000/dashboard"
        
        # Verify session cookie is set
        assert "session" in resp.cookies
        session_cookie = resp.cookies["session"]
        
        # Decode session token to verify payload
        payload = jwt.decode(session_cookie, "test_jwt_secret", algorithms=["HS256"])
        assert payload["user_id"] == "user-uuid-123"
        assert payload["username"] == "testuser"

# Test Marketplace Webhook Integration Endpoints
@patch("n3mo.api.marketplace.upsert_organization")
@patch("n3mo.api.marketplace.update_subscription")
@patch("n3mo.api.marketplace.save_license_key")
def test_marketplace_webhook_purchase_enterprise(mock_save_key, mock_update_sub, mock_upsert_org):
    mock_upsert_org.return_value = {"id": "org-uuid-456"}
    mock_update_sub.return_value = {"status": "active"}
    
    payload = {
        "action": "purchased",
        "marketplace_purchase": {
            "account": {
                "id": 1122,
                "login": "EnterpriseOrg",
                "type": "Organization"
            },
            "plan": {
                "name": "N3MO Enterprise Self-Hosted"
            }
        }
    }
    
    with patch.dict(os.environ, {"N3MO_LICENSE_SECRET": "test_jwt_secret"}):
        resp = client.post("/github/marketplace/webhook", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["status"] == "processed"
        assert data["plan"] == "enterprise"
        assert "license" in data
        assert "license_key" in data["license"]
        
        # Verify offline license key is a valid JWT
        token = data["license"]["license_key"]
        payload_decoded = jwt.decode(token, "test_jwt_secret", algorithms=["HS256"])
        assert payload_decoded["owner"] == "EnterpriseOrg"
        assert payload_decoded["plan_type"] == "enterprise"
        
        mock_upsert_org.assert_called_once_with(github_id=1122, name="EnterpriseOrg")
        mock_update_sub.assert_called_once()
        mock_save_key.assert_called_once()
