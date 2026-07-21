# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import logging
import hmac
import hashlib
import urllib.request
import urllib.error
import json
import time
import datetime as _dt
import jwt
from fastapi import APIRouter, FastAPI, Request, Header, HTTPException, BackgroundTasks

from n3mo.saas_db import get_user_by_username, get_subscription


logger = logging.getLogger("n3mo.api")
router = APIRouter()

# Configuration
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
N3MO_LICENSE_KEY = os.getenv("N3MO_LICENSE_KEY", "")
N3MO_SUBSCRIPTION_ACTIVE = os.getenv("N3MO_SUBSCRIPTION_ACTIVE", "false").lower() in ("true", "1", "yes")

def revoke_github_installation(installation_id: str):
    """Generate a GitHub App JWT and delete the installation."""
    app_id = os.getenv("GITHUB_APP_ID")
    private_key_env = os.getenv("GITHUB_APP_PRIVATE_KEY")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH") or os.getenv("GITHUB_PRIVATE_KEY_PATH")
    
    if not app_id:
        logger.error("Missing GITHUB_APP_ID for token revocation.")
        return False
        
    private_key = None
    if private_key_env:
        private_key = private_key_env
    elif private_key_path and os.path.exists(private_key_path):
        with open(private_key_path, "r") as f:
            private_key = f.read()
            
    if not private_key:
        logger.error("Missing GITHUB_APP_PRIVATE_KEY for token revocation.")
        return False
        
    try:
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": app_id
        }
        encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
        
        req = urllib.request.Request(
            f"https://api.github.com/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {encoded_jwt}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "N3MO-SaaS"
            },
            method="DELETE"
        )
        with urllib.request.urlopen(req) as _:
            logger.info(f"Successfully revoked GitHub App installation {installation_id}.")
            return True
    except Exception as e:
        logger.error(f"Failed to revoke GitHub App installation {installation_id}: {e}")
        return False


@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "n3mo-webhook-api"}


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    if not x_github_event:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    payload_bytes = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    logger.info(f"Received GitHub event: {x_github_event}")

    # Enforce SaaS-only Webhooks
    is_saas = os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")
    if not is_saas:
        logger.warning("Webhook endpoint hit, but SaaS mode is disabled.")
        return {"status": "error", "message": "GitHub Webhooks are a SaaS-exclusive feature. Run N3MO via CLI locally."}

    # Determine which secret to use for HMAC verification
    secret_to_use = GITHUB_WEBHOOK_SECRET
    user_db = None
    
    # Safely extract repository owner
    repository = payload.get("repository")
    if isinstance(repository, dict):
        owner = repository.get("owner")
        if isinstance(owner, dict):
            repo_owner_name = owner.get("login")
        else:
            repo_owner_name = None
    else:
        repo_owner_name = None

    if repo_owner_name:
        try:
            user_db = get_user_by_username(repo_owner_name)
            if not user_db:
                logger.warning(f"Webhook from unregistered user {repo_owner_name}, rejecting.")
                return {"status": "error", "message": "User is not registered on N3MO SaaS."}
                
            secret_from_db = user_db.get("webhook_secret")
            if secret_from_db:
                secret_to_use = str(secret_from_db)
        except Exception as e:
            logger.error(f"Database error fetching user {repo_owner_name}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error connecting to database.")

    # 1. VERIFY SIGNATURE FIRST
    if secret_to_use:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
        parts = x_hub_signature_256.split("=")
        if len(parts) != 2 or parts[0] != "sha256":
            raise HTTPException(status_code=400, detail="Invalid signature format")
        expected = hmac.new(secret_to_use.encode(), payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, parts[1]):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 2. CHECK EXPIRATION & REVOKE TOKEN (Only if signature is valid)
    if user_db:
        try:
            sub = get_subscription(str(user_db.get("id")), "user")
            is_expired = sub.get("status") in ("expired", "none")
            
            # Check the timestamp as a fallback
            if not is_expired and sub.get("expires_at") is not None:
                exp = sub["expires_at"]
                now = _dt.datetime.now(_dt.timezone.utc)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=_dt.timezone.utc)
                if exp < now:
                    is_expired = True
                    
            if is_expired:
                installation = payload.get("installation")
                installation_id = installation.get("id") if isinstance(installation, dict) else None
                if installation_id:
                    # Authenticated token revocation
                    revoke_github_installation(str(installation_id))
                return {"status": "error", "message": "Subscription expired. GitHub webhook token revoked."}
        except Exception as e:
            logger.error(f"Database error fetching subscription for {user_db.get('id')}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error connecting to database.")

    # 3. CORE LOGIC
    if x_github_event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize"]:
            # Run the checkout and analysis in a background task to respond instantly
            # In SaaS/Vercel mode, we trigger the Core Engine via GitHub Actions
            github_pat = os.getenv("GITHUB_PAT")
            if not github_pat:
                logger.error("Missing GITHUB_PAT. Cannot trigger Core Engine.")
                return {"status": "error", "message": "N3MO Core Engine is not configured (Missing PAT)."}
                
            n3mo_repo = os.getenv("N3MO_CENTRAL_REPO", "RajX-dev/N3MO")
            dispatch_url = f"https://api.github.com/repos/{n3mo_repo}/dispatches"
            
            target_repo = payload.get("repository", {}).get("full_name")
            pr_number = payload.get("number")
            
            dispatch_payload = {
                "event_type": "n3mo-analyze-pr",
                "client_payload": {
                    "repository": target_repo,
                    "pr_number": str(pr_number),
                    "user_id": str(user_db.get("id")) if user_db else "",
                    "installation_id": str(payload.get("installation", {}).get("id", "")) if isinstance(payload.get("installation"), dict) else ""
                }
            }
            
            req = urllib.request.Request(
                dispatch_url,
                data=json.dumps(dispatch_payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {github_pat}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                    "User-Agent": "N3MO-SaaS"
                },
                method="POST"
            )
            
            try:
                with urllib.request.urlopen(req) as _:
                    logger.info(f"Successfully triggered Core Engine for {target_repo} PR #{pr_number}")
                    return {"status": "accepted", "message": "Core Engine triggered successfully"}
            except Exception as e:
                logger.error(f"Failed to trigger Core Engine: {e}")
                return {"status": "error", "message": "Failed to wake up Core Engine"}

    return {"message": f"Event '{x_github_event}' ignored"}

# Standalone App for webhook_handler
app = FastAPI(
    title="N3MO GitHub App Webhook API",
    description="Listens to GitHub webhooks to run incremental impact analysis on Pull Requests.",
    version="0.1.0"
)
app.include_router(router)
