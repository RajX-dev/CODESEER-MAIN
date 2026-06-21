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
import urllib.request
import urllib.parse
import json
import logging
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query, Response, Depends, Cookie
from fastapi.responses import RedirectResponse
import warnings

# Suppress PyJWT InsecureKeyLengthWarning for short testing secrets
warnings.filterwarnings("ignore", message="The HMAC key is .* bytes long", module="jwt")

from n3mo.saas_db import upsert_user

logger = logging.getLogger("n3mo.api.auth")
router = APIRouter()

def get_oauth_config():
    """Retrieve GitHub OAuth configurations dynamically from environment."""
    return {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/callback"),
        "frontend_url": os.getenv("FRONTEND_DASHBOARD_URL", "/dashboard.html"),
        "session_secret": os.getenv("JWT_SESSION_SECRET", "super-secret-saas-session-key")
    }

def create_session_token(user_id: str, username: str) -> str:
    """Create a signed JWT session token for the user."""
    config = get_oauth_config()
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, config["session_secret"], algorithm="HS256")

def get_current_user_from_token(session: str = Cookie(None)) -> dict:
    """Verify session cookie and return user identity."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated: Session cookie missing")
    config = get_oauth_config()
    try:
        payload = jwt.decode(session, config["session_secret"], algorithms=["HS256"])
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username")
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Not authenticated: Session expired or invalid")

@router.get("/login")
def login_redirect():
    """Redirects the client to GitHub's OAuth authorization page."""
    config = get_oauth_config()
    if not config["client_id"]:
        raise HTTPException(status_code=500, detail="OAuth Configuration Error: GITHUB_CLIENT_ID not set")
    
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": "user:email read:org"
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@router.get("/callback")
def oauth_callback(response: Response, code: str = Query(None)):
    """Handles GitHub's OAuth redirect, requests token, fetches profile, and creates session."""
    if not code:
        raise HTTPException(status_code=400, detail="OAuth authorization code missing")

    config = get_oauth_config()

    # 1. Exchange auth code for GitHub access token
    token_url = "https://github.com/login/oauth/access_token"
    data = urllib.parse.urlencode({
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "redirect_uri": config["redirect_uri"]
    }).encode("utf-8")
    
    req = urllib.request.Request(
        token_url,
        data=data,
        headers={"Accept": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read().decode())
            github_token = token_data.get("access_token")
            if not github_token:
                logger.error(f"GitHub OAuth error: {token_data.get('error_description', 'No token returned')}")
                raise HTTPException(status_code=400, detail="Failed to obtain GitHub access token")
    except Exception as e:
        logger.error(f"GitHub token exchange request failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during OAuth exchange")

    # 2. Fetch authenticated user profile details from GitHub
    user_url = "https://api.github.com/user"
    user_req = urllib.request.Request(
        user_url,
        headers={
            "Authorization": f"Bearer {github_token}",
            "User-Agent": "N3MO-SaaS-Auth",
            "Accept": "application/vnd.github.v3+json"
        }
    )
    
    try:
        with urllib.request.urlopen(user_req) as resp:
            profile = json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"Failed to fetch GitHub profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user profile from GitHub")

    github_id = profile.get("id")
    username = profile.get("login")
    email = profile.get("email")
    avatar_url = profile.get("avatar_url")
    
    if not github_id or not username:
        raise HTTPException(status_code=400, detail="Incomplete profile returned from GitHub")

    # 3. Upsert user in local PostgreSQL database
    try:
        user = upsert_user(
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar_url,
            github_token=github_token
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
        
    if not user:
        raise HTTPException(status_code=500, detail="Failed to register user account in system database")

    # 4. Generate system JWT token and set as HttpOnly cookie
    session_token = create_session_token(user["id"], user["username"])
    response = RedirectResponse(url=config["frontend_url"])
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60, # 7 Days
        samesite="lax",
        secure=True
    )
    return response

@router.get("/me")
def get_user_profile(current_user: dict = Depends(get_current_user_from_token)):
    """Fetch profile data of the logged-in user."""
    return {
        "status": "success",
        "user_id": current_user["user_id"],
        "username": current_user["username"]
    }

@router.post("/logout")
def logout(response: Response):
    """Logs out user by clearing the session cookie."""
    response = Response(content=json.dumps({"status": "success", "message": "Logged out successfully"}), media_type="application/json")
    response.delete_cookie("session")
    return response
