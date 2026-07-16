import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from n3mo.api_server import app
from n3mo.api.auth import get_current_user_from_token

client = TestClient(app)

def test_admin_routes_require_admin():
    # Override dependency for a regular user
    app.dependency_overrides[get_current_user_from_token] = lambda: {
        "id": "user_id_123",
        "is_admin": False,
        "username": "regular_user"
    }

    # Attempt to access an admin endpoint
    response = client.get("/api/admin/users")
    
    # Should be forbidden
    assert response.status_code == 403
    assert response.json() == {"detail": "Admin privileges required"}

    # Clear overrides
    app.dependency_overrides = {}

@patch("n3mo.api.admin.get_all_users_with_subscriptions")
def test_admin_routes_allow_admin(mock_get_users):
    # Override dependency for an admin user
    app.dependency_overrides[get_current_user_from_token] = lambda: {
        "id": "admin_id_123",
        "is_admin": True,
        "username": "admin_user"
    }
    
    # Mock DB response
    mock_get_users.return_value = [{"id": "user1", "username": "RajX-dev"}]

    # Attempt to access an admin endpoint
    response = client.get("/api/admin/users")
    
    # Should succeed
    assert response.status_code == 200
    assert response.json() == {"users": [{"id": "user1", "username": "RajX-dev"}]}

    # Clear overrides
    app.dependency_overrides = {}
