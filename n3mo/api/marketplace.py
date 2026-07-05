# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import json
import hmac
import hashlib
import logging
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Header, HTTPException

from n3mo.saas_db import upsert_user, upsert_organization, update_subscription, save_license_key
from n3mo.license_validator import get_license_hash

logger = logging.getLogger("n3mo.api.marketplace")
router = APIRouter()

# Configuration
GITHUB_MARKETPLACE_SECRET = os.getenv("GITHUB_MARKETPLACE_SECRET", "")

def generate_license_jwt(owner_name: str, plan_type: str, max_loc: int, duration_days: int = 365) -> str:
    """Generate a cryptographically signed JWT license key for self-hosted Enterprise users."""
    private_key = os.getenv("N3MO_LICENSE_PRIVATE_KEY", "")
    secret_key = os.getenv("N3MO_LICENSE_SECRET", "")

    payload = {
        "owner": owner_name,
        "plan_type": plan_type,
        "max_loc": max_loc,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(days=duration_days)).timestamp())
    }

    if private_key:
        private_key = private_key.replace("\\n", "\n").strip()
        # Signs using RSA key
        return jwt.encode(payload, private_key, algorithm="RS256")
    elif secret_key:
        # Signs using symmetric key
        return jwt.encode(payload, secret_key.strip(), algorithm="HS256")
    else:
        # Fallback for local sandbox testing
        return jwt.encode(payload, "super-secret-saas-session-key", algorithm="HS256")

@router.post("/webhook")
async def marketplace_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    """Listens to GitHub Marketplace subscription events (purchases, plan changes, cancellations)."""
    body = await request.body()
    
    # Verify signature if secret is configured
    if GITHUB_MARKETPLACE_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
        parts = x_hub_signature_256.split("=")
        if len(parts) != 2 or parts[0] != "sha256":
            raise HTTPException(status_code=400, detail="Invalid signature format")
        
        expected = hmac.new(GITHUB_MARKETPLACE_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, parts[1]):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    action = payload.get("action")
    marketplace_purchase = payload.get("marketplace_purchase", {})
    account = marketplace_purchase.get("account", {})
    plan = marketplace_purchase.get("plan", {})

    if not action or not account or not plan:
        return {"status": "ignored", "reason": "Incomplete marketplace webhook structure"}

    github_id = account.get("id")
    name = account.get("login")
    account_type = account.get("type") # "User" or "Organization"
    plan_name = plan.get("name", "").lower() # e.g. "free", "pro", "enterprise"

    logger.info(f"Marketplace webhook: {action} plan '{plan_name}' for {account_type} '{name}'")

    # 1. Map billing plans
    if "enterprise" in plan_name:
        plan_type = "enterprise"
    elif "pro" in plan_name:
        plan_type = "pro"
    else:
        plan_type = "free"

    status = "active"
    if action == "cancelled":
        status = "cancelled"

    # 2. Provision User or Organization profile
    owner_id = None
    if account_type == "User":
        user = upsert_user(github_id=github_id, username=name)
        owner_id = user.get("id")
        owner_category = "user"
    elif account_type == "Organization":
        org = upsert_organization(github_id=github_id, name=name)
        owner_id = org.get("id")
        owner_category = "organization"
    else:
        return {"status": "ignored", "reason": f"Unknown account type: {account_type}"}

    if not owner_id:
        raise HTTPException(status_code=500, detail="Failed to resolve account owner ID in database")

    # 3. Synchronize Subscription status
    # Default plan duration is 1 year (or indefinite if auto-renewing, but let's set 365 days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=365) if status == "active" else datetime.now(timezone.utc)
    sub = update_subscription(
        owner_id=owner_id,
        owner_type=owner_category,
        plan_type=plan_type,
        status=status,
        expires_at=expires_at
    )

    # 4. Generate Enterprise Offline License Key if applicable
    license_info = None
    if plan_type == "enterprise" and status == "active":
        # Generate the JWT license key token
        license_jwt = generate_license_jwt(
            owner_name=name,
            plan_type="enterprise",
            max_loc=-1, # Unlimited LOC for self-hosted enterprise tier
            duration_days=365
        )
        key_hash = get_license_hash(license_jwt)
        
        # Save the hashed license record for audit
        save_license_key(
            owner_id=owner_id,
            owner_type=owner_category,
            key_hash=key_hash,
            plan_type="enterprise",
            max_loc=-1,
            expires_at=expires_at
        )
        license_info = {
            "license_key": license_jwt,
            "message": "Enterprise License Key generated. Copy and supply it to your N3MO_LICENSE_KEY variable."
        }

    return {
        "status": "processed",
        "action": action,
        "plan": plan_type,
        "subscription_status": sub.get("status"),
        "license": license_info
    }
