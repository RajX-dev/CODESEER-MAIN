import os
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from n3mo.saas_db import update_subscription

logger = logging.getLogger("n3mo.payments")
router = APIRouter()

LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "dummy_webhook_secret")

@router.post("/webhook/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None)
):
    """
    Handle incoming webhooks from LemonSqueezy.
    This upgrades the user's account to Pro when a payment is successful.
    """
    if not x_signature:
        raise HTTPException(status_code=400, detail="Missing signature header")

    payload_body = await request.body()
    
    # Verify the HMAC signature
    digest = hmac.new(
        LEMONSQUEEZY_WEBHOOK_SECRET.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(digest, x_signature):
        logger.error("Invalid LemonSqueezy webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = await request.json()
        event_name = data.get("meta", {}).get("event_name")
        custom_data = data.get("meta", {}).get("custom_data", {})
        
        # We passed the user's github_id via custom_data when creating the checkout
        github_id = custom_data.get("github_id")
        
        if event_name == "order_created" or event_name == "subscription_created":
            if github_id:
                logger.info(f"Payment successful! Upgrading github_id {github_id} to PRO")
                update_subscription(str(github_id), "user", "pro", "active")
            else:
                logger.warning("Received payment but no github_id found in custom_data")
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing LemonSqueezy webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
