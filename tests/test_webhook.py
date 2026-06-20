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
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from n3mo.api.webhook_handler import (
    app,
    calculate_repo_loc,
    format_impact_markdown,
    merge_impacts,
    post_github_comment
)

client = TestClient(app)

@pytest.fixture
def mock_repo_dir(tmp_path):
    # Create a mock repo directory with some source files
    repo = tmp_path / "my_repo"
    repo.mkdir()
    
    file_a = repo / "file_a.py"
    file_a.write_text("def run():\n    print('hello')\n" * 100, encoding="utf-8") # 200 lines
    
    file_b = repo / "file_b.py"
    file_b.write_text("class Test:\n    pass\n" * 50, encoding="utf-8") # 100 lines
    
    return str(repo)

def test_calculate_repo_loc(mock_repo_dir):
    loc = calculate_repo_loc(mock_repo_dir)
    # 200 lines in file_a + 100 lines in file_b = 300 lines total
    assert loc == 300

def test_format_impact_markdown():
    merged = {
        "func_a": {
            "status": "Modified",
            "file_path": "src/api.py",
            "line": 45,
            "callers": [
                {"source": "caller_direct", "file_path": "src/cli.py", "line": 10, "depth": 1},
                {"source": "caller_indirect", "file_path": "src/main.py", "line": 5, "depth": 2}
            ]
        },
        "func_deleted": {
            "status": "Deleted",
            "file_path": "src/old.py",
            "line": 12,
            "callers": []
        }
    }
    
    markdown = format_impact_markdown(merged, "owner/repo", 42, 5000)
    
    assert "### ◈ N3MO Pull Request Impact Analysis" in markdown
    assert "PR #42" in markdown
    assert "func_a" in markdown
    assert "func_deleted" in markdown
    assert "Modified" in markdown
    assert "Deleted" in markdown
    assert "caller_direct" in markdown
    assert "caller_indirect" in markdown

def test_merge_impacts():
    base = {
        "func_a": {"file_path": "src/a.py", "line": 10, "callers": []},
        "func_b": {"file_path": "src/b.py", "line": 20, "callers": []}
    }
    head = {
        "func_a": {"file_path": "src/a.py", "line": 12, "callers": [{"source": "call", "file_path": "src/m.py", "line": 4, "depth": 1}]},
        "func_c": {"file_path": "src/c.py", "line": 30, "callers": []}
    }
    
    merged = merge_impacts(base, head)
    
    assert merged["func_a"]["status"] == "Modified"
    assert len(merged["func_a"]["callers"]) == 1
    assert merged["func_b"]["status"] == "Deleted"
    assert merged["func_c"]["status"] == "Added"

@patch("urllib.request.urlopen")
def test_post_comment_local_fallback(mock_urlopen):
    # No credentials in env
    with patch.dict(os.environ, {}, clear=True):
        res = post_github_comment("owner/repo", 1, "test body")
        assert res["status"] == "printed_locally"
        mock_urlopen.assert_not_called()

@patch("urllib.request.urlopen")
def test_post_comment_pat(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"id": 12345}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    with patch.dict(os.environ, {"GITHUB_TOKEN": "secret_pat"}):
        res = post_github_comment("owner/repo", 1, "test body")
        assert res["status"] == "posted"
        assert res["comment_id"] == 12345
        mock_urlopen.assert_called_once()

def test_webhook_signature_required():
    with patch("n3mo.api.webhook_handler.GITHUB_WEBHOOK_SECRET", "my_secret"):
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
        
        with patch("n3mo.api.webhook_handler.handle_pull_request") as mock_handle:
            mock_handle.return_value = {"status": "processed"}
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
            mock_handle.assert_called_once()

@patch("n3mo.api.webhook_handler.checkout_repo")
@patch("n3mo.api.webhook_handler.calculate_repo_loc")
@patch("n3mo.api.webhook_handler.post_github_comment")
def test_webhook_loc_exceeded(mock_post_comment, mock_calculate_loc, mock_checkout):
    mock_checkout.return_value = "/mock/repo/dir"
    mock_calculate_loc.return_value = 20000 # exceeds 15k limit
    
    payload = {
        "action": "opened",
        "number": 42,
        "repository": {"full_name": "owner/repo", "clone_url": "https://github.com/owner/repo.git"},
        "pull_request": {
            "base": {"sha": "base123"},
            "head": {"sha": "head456"}
        }
    }
    
    with patch.dict(os.environ, {"N3MO_SAAS_MODE": "true"}, clear=True):
        resp = client.post("/webhook", json=payload, headers={"X-GitHub-Event": "pull_request"})
        assert resp.status_code == 200
        # Should call post_github_comment with the warning message
        mock_post_comment.assert_called_once()
        args, kwargs = mock_post_comment.call_args
        assert "⚠️ N3MO Tier Limit Reached" in args[2]
        assert "20,000 lines of code" in args[2]

@patch("n3mo.api.webhook_handler.checkout_repo")
@patch("n3mo.api.webhook_handler.calculate_repo_loc")
@patch("n3mo.api.webhook_handler.get_changed_files")
@patch("n3mo.api.webhook_handler.run_indexer_for_path")
@patch("n3mo.api.webhook_handler.get_project_id")
@patch("n3mo.api.webhook_handler.get_impact_for_changed_files")
@patch("n3mo.api.webhook_handler.post_github_comment")
def test_webhook_full_analysis_flow(
    mock_post_comment,
    mock_get_impact,
    mock_get_project_id,
    mock_run_indexer,
    mock_get_changed_files,
    mock_calculate_loc,
    mock_checkout
):
    mock_checkout.return_value = "/mock/repo/dir"
    mock_calculate_loc.return_value = 5000 # within 15k limit
    mock_get_changed_files.return_value = ["src/main.py"]
    mock_get_project_id.return_value = "project-uuid"
    
    # Mock impact dictionaries
    base_impacts = {
        "old_func": {"file_path": "src/main.py", "line": 10, "callers": []}
    }
    head_impacts = {
        "new_func": {"file_path": "src/main.py", "line": 20, "callers": [{"source": "call", "file_path": "src/app.py", "line": 5, "depth": 1}]}
    }
    mock_get_impact.side_effect = [base_impacts, head_impacts]
    
    payload = {
        "action": "opened",
        "number": 101,
        "repository": {"full_name": "owner/repo", "clone_url": "https://github.com/owner/repo.git"},
        "pull_request": {
            "base": {"sha": "base123"},
            "head": {"sha": "head456"}
        }
    }
    
    with patch.dict(os.environ, {"N3MO_SAAS_MODE": "true"}):
        resp = client.post("/webhook", json=payload, headers={"X-GitHub-Event": "pull_request"})
        assert resp.status_code == 200
    
    # Verify indexer ran for both base and head
    assert mock_run_indexer.call_count == 2
    # Verify post comment was called with analysis report
    mock_post_comment.assert_called_once()
    args, kwargs = mock_post_comment.call_args
    assert "### ◈ N3MO Pull Request Impact Analysis" in args[2]
    assert "old_func" in args[2]
    assert "new_func" in args[2]

@patch("n3mo.api.webhook_handler.checkout_repo")
@patch("n3mo.api.webhook_handler.post_github_comment")
def test_webhook_self_hosted_blocked_without_license(mock_post_comment, mock_checkout):
    mock_checkout.return_value = "/mock/repo/dir"
    
    payload = {
        "action": "opened",
        "number": 42,
        "repository": {"full_name": "owner/repo", "clone_url": "https://github.com/owner/repo.git"},
        "pull_request": {
            "base": {"sha": "base123"},
            "head": {"sha": "head456"}
        }
    }
    
    with patch.dict(os.environ, {"N3MO_SAAS_MODE": "false", "N3MO_LICENSE_KEY": ""}, clear=True):
        resp = client.post("/webhook", json=payload, headers={"X-GitHub-Event": "pull_request"})
        assert resp.status_code == 200
        mock_post_comment.assert_called_once()
        args, kwargs = mock_post_comment.call_args
        assert "❌ N3MO Self-Hosted License Required" in args[2]

def test_gumroad_webhook():
    # Gumroad sends form data URL-encoded
    payload_body = b"github_id=9999&price=1900&email=test%40example.com"
    correct_hash = hmac.new(b"dummy_webhook_secret", payload_body, hashlib.sha256).hexdigest()
    
    with patch("n3mo.api.gumroad_webhook.update_subscription") as mock_update:
        from n3mo.api_server import app as main_app
        client = TestClient(main_app)
        
        resp = client.post(
            "/api/webhook/gumroad",
            content=payload_body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Gumroad-Signature": correct_hash
            }
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "success"}
        mock_update.assert_called_once_with("9999", "user", "pro", "active")

