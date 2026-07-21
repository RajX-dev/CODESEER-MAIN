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
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Header, HTTPException

from n3mo.saas_db import upsert_user, upsert_organization, update_subscription, save_license_key, check_rate_limit_db, check_webhook_replay_db
from n3mo.license_validator import get_license_hash

logger = logging.getLogger("n3mo.api.marketplace")
router = APIRouter()

# Configuration
GITHUB_MARKETPLACE_SECRET = os.getenv("GITHUB_MARKETPLACE_SECRET", "")

def is_saas_mode() -> bool:
    return os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")

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
        # Prevent fallback generation if keys are missing
        raise RuntimeError("Missing N3MO_LICENSE_PRIVATE_KEY or N3MO_LICENSE_SECRET. Cannot generate secure licenses.")

@router.post("/webhook")
async def marketplace_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_delivery: str = Header(None)
):
    """Listens to GitHub Marketplace subscription events (purchases, plan changes, cancellations)."""
    body = await request.body()
    
    if is_saas_mode() and not GITHUB_MARKETPLACE_SECRET:
        raise HTTPException(status_code=500, detail="GITHUB_MARKETPLACE_SECRET is not configured.")

    # 1. Verify signature
    if GITHUB_MARKETPLACE_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
        parts = x_hub_signature_256.split("=")
        if len(parts) != 2 or parts[0] != "sha256":
            raise HTTPException(status_code=400, detail="Invalid signature format")
        
        expected = hmac.new(GITHUB_MARKETPLACE_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, parts[1]):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 2. Replay Protection
    if x_github_delivery:
        if not check_webhook_replay_db(x_github_delivery):
            return {"status": "ignored", "reason": "Webhook delivery already processed"}

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

    if not github_id or not name:
        return {"status": "ignored", "reason": "Missing github_id or login"}

    # 3. Rate Limiting (per GitHub ID)
    if not check_rate_limit_db(f"marketplace_{github_id}", 5, 60):
        raise HTTPException(status_code=429, detail="Too many marketplace requests. Please try again later.")

    # 4. Strict account type validation
    if account_type not in ("User", "Organization"):
        return {"status": "ignored", "reason": f"Unknown account type: {account_type}"}

    logger.info(f"Marketplace webhook: {action} plan '{plan_name}' for {account_type} '{name}'")

    # 5. Strict plan mapping
    if plan_name == "enterprise":
        plan_type = "enterprise"
    elif plan_name == "pro":
        plan_type = "pro"
    elif plan_name == "free":
        plan_type = "free"
    else:
        return {"status": "ignored", "reason": f"Unknown plan name: {plan_name}"}

    status = "active"
    if action == "cancelled":
        status = "cancelled"

    try:
        # 6. Provision User or Organization profile
        owner_id = None
        if account_type == "User":
            user = upsert_user(github_id=github_id, username=name)
            owner_id = user.get("id")
            owner_category = "user"
        elif account_type == "Organization":
            org = upsert_organization(github_id=github_id, name=name)
            owner_id = org.get("id")
            owner_category = "organization"

        if not owner_id:
            raise HTTPException(status_code=500, detail="Failed to resolve account owner ID in database")

        # 7. Synchronize Subscription status
        # If cancelled, expire immediately (in the past) to invalidate
        if status == "active":
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        else:
            expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            
        sub = update_subscription(
            owner_id=owner_id,
            owner_type=owner_category,
            plan_type=plan_type,
            status=status,
            expires_at=expires_at
        )

        # 8. Generate Enterprise Offline License Key if applicable
        license_info_msg = None
        if plan_type == "enterprise" and status == "active":
            # Generate the JWT license key token
            license_jwt = generate_license_jwt(
                owner_name=name,
                plan_type="enterprise",
                max_loc=-1, # Unlimited LOC for self-hosted enterprise tier
                duration_days=365
            )
            key_hash = get_license_hash(license_jwt)
            
            # Log audit fields (would ideally go into DB)
            logger.info(f"AUDIT: License generated. Delivery ID: {x_github_delivery}, Signed At: {datetime.now(timezone.utc).isoformat()}")

            # Save the hashed license record for audit
            save_license_key(
                owner_id=owner_id,
                owner_type=owner_category,
                key_hash=key_hash,
                plan_type="enterprise",
                max_loc=-1,
                expires_at=expires_at
            )
            license_info_msg = "Enterprise License Key generated. Please check your email or dashboard."

        return {
            "status": "processed",
            "action": action,
            "plan": plan_type,
            "subscription_status": sub.get("status"),
            "license_message": license_info_msg
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database/Internal error processing marketplace webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while processing subscription")

