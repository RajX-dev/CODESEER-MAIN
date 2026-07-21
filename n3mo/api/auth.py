# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import urllib.request
import urllib.parse
import json
import logging
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query, Response, Depends, Cookie
from fastapi.responses import RedirectResponse
import warnings

from n3mo.saas_db import upsert_user, get_subscription, update_subscription
from n3mo.pricing import TRIAL_DAYS, get_tier

# Suppress PyJWT InsecureKeyLengthWarning for short testing secrets
warnings.filterwarnings("ignore", message="The HMAC key is .* bytes long", module="jwt")

logger = logging.getLogger("n3mo.api.auth")
router = APIRouter()

def get_oauth_config():
    """Retrieve GitHub OAuth configurations dynamically from environment."""
    return {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/callback"),
        "frontend_url": os.getenv("FRONTEND_DASHBOARD_URL", "/dashboard.html"),
        "session_secret": os.getenv("JWT_SESSION_SECRET", "")
    }

def is_saas_mode() -> bool:
    return os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")

def validate_frontend_url(url: str) -> str:
    """Ensure frontend_url is safe to redirect to (prevents Open Redirect)."""
    if url.startswith("/") or url.startswith("http://localhost"):
        return url
    if is_saas_mode() and url.startswith("https://n3mo.shop"):
        return url
    # Fallback safe relative path
    return "/dashboard.html"

def provision_user_trial(user_id: str):
    """Provisions a 15-day free trial if the user has no existing subscription."""
    try:
        current_sub = get_subscription(user_id, "user")
        if current_sub.get("status") == "none":
            pro_tier = get_tier("pro")
            expires_at = datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)
            update_subscription(
                user_id, "user", "pro", "trialing",
                expires_at=expires_at,
                repos_limit=pro_tier["repos_limit"],
                lines_of_code_limit=pro_tier["max_total_loc"],
                loc_per_repo_limit=pro_tier["loc_per_repo"]
            )
    except Exception as e:
        logger.error(f"Database Error provisioning trial for {user_id}: {e}")
        # Don't throw 500, let them log in, but they won't have a trial.
        # Admin can resolve or they can contact support.

def create_session_token(user_id: str, github_id: int) -> str:
    """Create a signed JWT session token for the user using immutable fields."""
    config = get_oauth_config()
    secret = config["session_secret"] or "super-secret-saas-session-key"
    if is_saas_mode() and not config["session_secret"]:
        raise ValueError("JWT_SESSION_SECRET must be explicitly set in SaaS mode.")
        
    payload = {
        "user_id": user_id,
        "github_id": github_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def get_current_user_from_token(session: str = Cookie(None)) -> dict:
    """Verify session cookie and return user identity."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated: Session cookie missing")
    config = get_oauth_config()
    secret = config["session_secret"] or "super-secret-saas-session-key"
    
    try:
        payload = jwt.decode(session, secret, algorithms=["HS256"])
        return {
            "user_id": payload.get("user_id"),
            "github_id": payload.get("github_id")
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Not authenticated: Session expired or invalid")

@router.get("/login")
def login_redirect(response: Response):
    """Redirects the client to GitHub's OAuth authorization page, or mocks login if missing config."""
    config = get_oauth_config()
    safe_redirect_url = validate_frontend_url(config["frontend_url"])
    is_secure_cookie = is_saas_mode() or config["redirect_uri"].startswith("https://")
    
    if not config["client_id"] or config["client_id"] == "mock":
        if is_saas_mode():
            raise HTTPException(status_code=500, detail="GitHub OAuth not configured. Cannot bypass in production.")
            
        logger.warning("Mock login bypass active! Creating dummy session.")
        user = upsert_user(
            github_id=12345678,
            username="test_user",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/12345678?v=4",
            github_token="mock_token"
        )
        
        provision_user_trial(user["id"])
            
        session_token = create_session_token(user["id"], user["github_id"])
        resp = RedirectResponse(url=safe_redirect_url)
        resp.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60, # 7 Days
            samesite="lax",
            secure=is_secure_cookie
        )
        return resp
    
    # Generate CSRF state token
    oauth_state = secrets.token_urlsafe(32)
    
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "state": oauth_state,
        "scope": "user:email read:org",
        "prompt": "consent"
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    
    resp = RedirectResponse(url)
    resp.set_cookie(
        key="oauth_state",
        value=oauth_state,
        httponly=True,
        max_age=600, # 10 minutes
        samesite="lax",
        secure=is_secure_cookie
    )
    return resp

@router.get("/callback")
def oauth_callback(
    response: Response, 
    code: str = Query(None), 
    state: str = Query(None), 
    oauth_state: str = Cookie(None)
):
    """Handles GitHub's OAuth redirect, requests token, fetches profile, and creates session."""
    if not code:
        raise HTTPException(status_code=400, detail="OAuth authorization code missing")
        
    if not state or state != oauth_state:
        raise HTTPException(status_code=400, detail="CSRF warning: OAuth state mismatch")

    config = get_oauth_config()
    safe_redirect_url = validate_frontend_url(config["frontend_url"])
    is_secure_cookie = is_saas_mode() or config["redirect_uri"].startswith("https://")

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

    # 4. Provision 15-day trial if no subscription exists
    provision_user_trial(user["id"])

    # 5. Generate system JWT token and set as HttpOnly cookie
    session_token = create_session_token(user["id"], user["github_id"])
    resp = RedirectResponse(url=safe_redirect_url)
    resp.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60, # 7 Days
        samesite="lax",
        secure=is_secure_cookie
    )
    # Clear the OAuth state cookie
    resp.delete_cookie("oauth_state", secure=is_secure_cookie, httponly=True, samesite="lax")
    return resp

@router.get("/me")
def get_user_profile(current_user: dict = Depends(get_current_user_from_token)):
    """Fetch profile data of the logged-in user."""
    # We fetch the latest username from DB since github_id is immutable but username can change.
    # For a real implementation, we would query the user table here.
    return {
        "status": "success",
        "user_id": current_user["user_id"],
        "github_id": current_user["github_id"]
    }

@router.post("/logout")
def logout(response: Response):
    """Logs out user by clearing the session cookie."""
    is_secure_cookie = is_saas_mode()
    response = Response(content=json.dumps({"status": "success", "message": "Logged out successfully"}), media_type="application/json")
    response.delete_cookie(
        key="session",
        path="/",
        secure=is_secure_cookie,
        httponly=True,
        samesite="lax"
    )
    return response
