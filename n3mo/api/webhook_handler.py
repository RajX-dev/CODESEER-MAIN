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
import logging
import hmac
import hashlib
import subprocess
import urllib.request
import urllib.error
import json
from fastapi import APIRouter, FastAPI, Request, Header, HTTPException, BackgroundTasks

from n3mo.run_indexer import run_indexer_for_path
from n3mo.database import get_connection, release_connection
from n3mo.crawler import crawl_directory
from n3mo.saas_db import upsert_user, upsert_organization, get_subscription
from n3mo.license_validator import verify_license_key

logger = logging.getLogger("n3mo.api")

router = APIRouter()

# Configuration
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
N3MO_LICENSE_KEY = os.getenv("N3MO_LICENSE_KEY", "")
N3MO_SUBSCRIPTION_ACTIVE = os.getenv("N3MO_SUBSCRIPTION_ACTIVE", "false").lower() in ("true", "1", "yes")

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
    
    # In SaaS mode, we use the user's personal webhook secret
    is_saas = os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")
    if is_saas:
        repo_owner_name = payload.get("repository", {}).get("owner", {}).get("login")
        if repo_owner_name:
            from n3mo.saas_db import get_user_by_username
            user_db = get_user_by_username(repo_owner_name)
            if user_db:
                secret_from_db = user_db.get("webhook_secret")
                if secret_from_db:
                    secret_to_use = str(secret_from_db)

    # Verify signature if a secret is configured (either global or personal)
    if secret_to_use:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
        parts = x_hub_signature_256.split("=")
        if len(parts) != 2 or parts[0] != "sha256":
            raise HTTPException(status_code=400, detail="Invalid signature format")
        expected = hmac.new(secret_to_use.encode(), payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, parts[1]):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

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
                    "user_id": str(user_db.get("id")) if 'user_db' in locals() and user_db else ""
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
                with urllib.request.urlopen(req) as resp:
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
