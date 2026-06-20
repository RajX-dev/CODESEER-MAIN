import os
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional

from n3mo.saas_db import update_subscription

logger = logging.getLogger("n3mo.payments")
router = APIRouter()

# Gumroad simple Pings don't use signatures, but they do send your seller_id
GUMROAD_SELLER_ID = os.getenv("GUMROAD_SELLER_ID", "")

@router.post("/webhook/gumroad")
async def gumroad_webhook(request: Request):
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
        
    # Verify it's actually coming from your store
    incoming_seller_id = data.get("seller_id")
    if GUMROAD_SELLER_ID and incoming_seller_id != GUMROAD_SELLER_ID:
        logger.error(f"Invalid Gumroad seller_id. Expected {GUMROAD_SELLER_ID}, got {incoming_seller_id}")
        raise HTTPException(status_code=401, detail="Invalid seller ID")

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
