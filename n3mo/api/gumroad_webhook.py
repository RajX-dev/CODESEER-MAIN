import os
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Header, Form
from typing import Optional

from n3mo.saas_db import update_subscription

logger = logging.getLogger("n3mo.payments")
router = APIRouter()

# Note: You don't need a secret for testing initially, but it's good practice.
# In Gumroad, you can find this under your advanced settings.
GUMROAD_WEBHOOK_SECRET = os.getenv("GUMROAD_WEBHOOK_SECRET", "dummy_webhook_secret")

@router.post("/webhook/gumroad")
async def gumroad_webhook(
    request: Request,
    x_gumroad_signature: Optional[str] = Header(None)
):
    """
    Handle incoming webhooks from Gumroad.
    This upgrades the user's account to Pro when a payment is successful.
    """
    payload_body = await request.body()
    
    # Gumroad sends form data usually, so we can parse it
    try:
        data = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data")
        
    # If a secret is configured, verify the HMAC signature
    # (Optional for simple testing, but required for production security)
    if GUMROAD_WEBHOOK_SECRET and GUMROAD_WEBHOOK_SECRET != "dummy_webhook_secret":
        if not x_gumroad_signature:
            raise HTTPException(status_code=400, detail="Missing signature header")
            
        digest = hmac.new(
            GUMROAD_WEBHOOK_SECRET.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(digest, x_gumroad_signature):
            logger.error("Invalid Gumroad webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        # Gumroad passes custom fields in the form data
        # We assume you added a custom field named "github_id" to your Gumroad product
        github_id = data.get("github_id")
        
        # We only want to process actual successful sales
        # Gumroad doesn't always send an event_name, it's just a POST on sale
        # But we can check if there's a price and email.
        if github_id:
            logger.info(f"Payment successful via Gumroad! Upgrading github_id {github_id} to PRO")
            update_subscription(str(github_id), "user", "pro", "active")
        else:
            logger.warning("Received payment but no github_id found in Gumroad custom fields")
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing Gumroad webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
