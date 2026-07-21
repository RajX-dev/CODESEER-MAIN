# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import logging
import json
import time
from fastapi import FastAPI, HTTPException, Request, Depends, Query
import uvicorn
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from n3mo.core.run_indexer import run_indexer_for_path
from n3mo.core.database import get_connection
from n3mo.cli.cli import get_code_context
from n3mo.api.webhook_handler import router as webhook_router
from n3mo.api.auth import router as auth_router
from n3mo.api.marketplace import router as marketplace_router
from n3mo.api.auth import get_current_user_from_token
from n3mo.api.entitlement import require_active_subscription
from n3mo.saas_db import (
    get_subscription, get_user_by_id, get_user_by_github_id, update_subscription,
    get_user_repo_loc_stats, save_payment_order, update_payment_order_status,
    get_payment_order, check_rate_limit_db
)
from n3mo.pricing import PRICING_TIERS, RAZORPAY_CONFIG, get_tier, calculate_upgrade_bonus_days, validate_eligibility
import razorpay  # type: ignore
import hmac
import hashlib
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="N3MO Code Intelligence API Server",
    description="REST endpoints for repository indexing and impact analysis",
    version="1.0.0"
)

app.include_router(webhook_router, prefix="/github")
app.include_router(marketplace_router, prefix="/github/marketplace", tags=["Marketplace"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

def is_saas_mode() -> bool:
    return os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_123")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "secret")

if is_saas_mode():
    if RAZORPAY_KEY_ID == "rzp_test_123" or "test_" in RAZORPAY_KEY_ID:
        raise RuntimeError("RAZORPAY_KEY_ID must be configured for production SaaS mode")
    required_vars = ["JWT_SESSION_SECRET", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_WEBHOOK_SECRET", "N3MO_DB_ENCRYPTION_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables for SaaS mode: {', '.join(missing)}")

ADMIN_GITHUB_IDS = set(int(x) for x in os.getenv("ADMIN_GITHUB_IDS", "").split(",") if x.strip().isdigit())
def check_rate_limit(key: str, limit: int, window: int):
    if not check_rate_limit_db(key, limit, window):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

class IndexRequest(BaseModel):
    target_dir: str

@app.get("/health")
def health():
    return {"status": "healthy", "service": "n3mo-api"}

@app.post("/index")
def trigger_indexing(req: IndexRequest, current_user: dict = Depends(get_current_user_from_token)):
    target_dir = os.path.abspath(req.target_dir)
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=400, detail=f"Directory '{target_dir}' does not exist.")
    
    success, summary = run_indexer_for_path(target_dir)
    if not success:
        raise HTTPException(status_code=500, detail=summary)
    
    return {"status": "success", "summary": summary}


# ---------------------------------------------------------------------------
# Billing endpoints
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    tier_id: str
    discount: str = ""

@app.post("/api/billing/create-order")
def create_order(req: CreateOrderRequest, current_user: dict = Depends(get_current_user_from_token)):
    """Create a Razorpay one-time order for the requested tier."""
    github_id_str = str(current_user["github_id"])
    check_rate_limit(f"create_order_{github_id_str}", 5, 60)

    tier = get_tier(req.tier_id)
    if not tier:
        raise HTTPException(status_code=400, detail=f"Unknown tier: '{req.tier_id}'")

    user_id = str(current_user["user_id"])
    key_id = RAZORPAY_KEY_ID

    if req.discount:
        raise HTTPException(status_code=400, detail="Discounts not supported via this endpoint")

    # --- LOC eligibility check ---
    loc_stats = get_user_repo_loc_stats(user_id)
    per_repo_locs = [r["loc"] for r in loc_stats["per_repo"]]
    eligible, err_msg = validate_eligibility(
        req.tier_id, loc_stats["total_repos"], per_repo_locs
    )
    if not eligible:
        raise HTTPException(status_code=400, detail=err_msg)

    # --- Calculate upgrade bonus days ---
    current_sub = get_subscription(user_id, "user")
    bonus_days = 0
    if current_sub.get("status") == "active" and current_sub.get("expires_at"):
        bonus_days = calculate_upgrade_bonus_days(current_sub["expires_at"])

    # --- Create Razorpay Order ---
    try:
        key_secret = RAZORPAY_KEY_SECRET
        client = razorpay.Client(auth=(key_id, key_secret))

        order_payload = {
            "amount": tier["price_in_cents"],
            "currency": RAZORPAY_CONFIG["currency"],
            "receipt": f"rcpt_{github_id_str}_{req.tier_id}",
            "notes": {
                "github_id": github_id_str,
                "tier_id": req.tier_id,
                "bonus_days": str(bonus_days),
            },
        }
        order = client.order.create(order_payload)

        # Persist order for audit
        save_payment_order(
            user_id=user_id,
            order_id=order["id"],
            tier_id=req.tier_id,
            amount_paise=tier["price_in_cents"],
            currency=str(RAZORPAY_CONFIG["currency"]),
        )

        return {
            "order_id": order["id"],
            "key_id": key_id,
            "amount_cents": tier["price_in_cents"],
            "currency": RAZORPAY_CONFIG["currency"],
            "tier_id": req.tier_id,
            "bonus_days": bonus_days,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating Razorpay order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    tier_id: str = "pro"

@app.post("/api/billing/verify-payment")
def verify_payment(req: VerifyPaymentRequest, current_user: dict = Depends(get_current_user_from_token)):
    """Verify Razorpay signature, activate subscription."""
    tier = get_tier(req.tier_id)
    if not tier:
        raise HTTPException(status_code=400, detail=f"Unknown tier: '{req.tier_id}'")

    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        client.utility.verify_payment_signature({
            "razorpay_order_id": req.razorpay_order_id,
            "razorpay_payment_id": req.razorpay_payment_id,
            "razorpay_signature": req.razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # Look up stored order to verify amount
    stored_order = get_payment_order(req.razorpay_order_id)
    if not stored_order:
        raise HTTPException(status_code=404, detail="Payment order not found")
    
    # Ideally use a DB lock here, but for now we rely on strict state checks
    if stored_order.get("status") == "paid":
        return {"status": "success", "message": "Payment already processed."}
    
    if stored_order["amount_cents"] != tier["price_in_cents"]:
        raise HTTPException(status_code=400, detail="Amount mismatch")

    user_id = str(current_user["user_id"])

    # Calculate new expiry (30 days + bonus from mid-cycle upgrade)
    current_sub = get_subscription(user_id, "user")
    bonus_days = 0
    if current_sub.get("status") == "active" and current_sub.get("expires_at"):
        bonus_days = calculate_upgrade_bonus_days(current_sub["expires_at"])

    new_expires = datetime.now(timezone.utc) + timedelta(
        days=tier["billing_cycle_days"] + bonus_days
    )

    update_subscription(
        user_id, "user", req.tier_id, "active",
        expires_at=new_expires,
        repos_limit=tier["repos_limit"],
        lines_of_code_limit=tier["max_total_loc"],
        loc_per_repo_limit=tier["loc_per_repo"],
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_order_id=req.razorpay_order_id,
        upgrade_bonus_days=bonus_days,
    )

    update_payment_order_status(
        req.razorpay_order_id, "paid", payment_id=req.razorpay_payment_id
    )

    return {
        "status": "success",
        "message": f"Payment verified, upgraded to {tier['name']}.",
        "expires_at": new_expires.isoformat(),
        "bonus_days": bonus_days,
    }


@app.post("/api/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """Handle Razorpay payment webhooks (payment.authorized, payment.failed)."""
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    if is_saas_mode() and not webhook_secret:
        raise HTTPException(status_code=500, detail="RAZORPAY_WEBHOOK_SECRET must be set in production")
    elif not webhook_secret:
        logging.warning("RAZORPAY_WEBHOOK_SECRET not configured, skipping webhook")
        return {"status": "ignored"}

    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    expected = hmac.new(
        webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logging.warning("Razorpay webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id", "")
    payment_id = payment_entity.get("id", "")

    if event in ("payment.authorized", "order.paid"):
        stored = get_payment_order(order_id)
        if stored and stored.get("status") != "paid":
            tier = get_tier(stored["tier_id"])
            if tier:
                user_id = str(stored["user_owner_id"])
                current_sub = get_subscription(user_id, "user")
                bonus_days = 0
                if current_sub.get("status") == "active" and current_sub.get("expires_at"):
                    bonus_days = calculate_upgrade_bonus_days(current_sub["expires_at"])

                new_expires = datetime.now(timezone.utc) + timedelta(
                    days=tier["billing_cycle_days"] + bonus_days
                )
                update_subscription(
                    user_id, "user", stored["tier_id"], "active",
                    expires_at=new_expires,
                    repos_limit=tier["repos_limit"],
                    lines_of_code_limit=tier["max_total_loc"],
                    loc_per_repo_limit=tier["loc_per_repo"],
                    razorpay_payment_id=payment_id,
                    razorpay_order_id=order_id,
                    upgrade_bonus_days=bonus_days,
                )
                update_payment_order_status(order_id, "paid", payment_id=payment_id)
                logging.info(f"Webhook: activated {stored['tier_id']} for user {user_id}")

    elif event == "payment.failed":
        if order_id:
            update_payment_order_status(order_id, "failed", payment_id=payment_id)
            logging.warning(f"Webhook: payment failed for order {order_id}")

    return {"status": "ok"}


@app.get("/api/billing/pricing")
def get_pricing():
    """Public endpoint returning all tier definitions for frontend rendering."""
    return {"tiers": PRICING_TIERS}

@app.get("/api/user/dashboard-data")
def get_dashboard_data(current_user: dict = Depends(get_current_user_from_token)):
    """Fetch all data needed for the user dashboard."""
    user_id = current_user["user_id"]
    user_db = get_user_by_id(user_id)
    if not user_db:
        raise HTTPException(status_code=401, detail="User not found in database. Please re-authenticate.")
        
    subscription = get_subscription(user_id, "user")
    
    loc_stats = get_user_repo_loc_stats(user_id)
    loc_limit = subscription.get("lines_of_code_limit") or 0
    loc_usage_percentage = (loc_stats["total_loc"] / loc_limit * 100) if loc_limit > 0 else 0
    
    days_until_expiry = 0
    expiry_warning = False
    
    if subscription.get("status") == "active" and subscription.get("expires_at"):
        days_until_expiry = calculate_upgrade_bonus_days(subscription["expires_at"])
        expiry_warning = days_until_expiry <= 7
    
    # Scrub sensitive secrets to prevent client-side leaks
    is_expired_or_none = subscription.get("status") in ("expired", "none")
    safe_webhook_secret = "EXPIRED" if is_expired_or_none else user_db.get("webhook_secret")
    
    # Strip payment IDs so they never reach the developer console
    subscription.pop("razorpay_payment_id", None)
    subscription.pop("razorpay_order_id", None)
    
    return {
        "status": "success",
        "user": {
            "username": user_db.get("username"),
            "github_id": user_db.get("github_id"),
            "avatar_url": user_db.get("avatar_url")
        },
        "subscription": subscription,
        "webhook_secret": safe_webhook_secret,
        "loc_stats": loc_stats,
        "loc_limit": loc_limit,
        "repos_limit": subscription.get("repos_limit") or 0,
        "loc_per_repo_limit": subscription.get("loc_per_repo_limit") or 0,
        "days_until_expiry": days_until_expiry,
        "expiry_warning": expiry_warning,
        "loc_usage_percentage": min(loc_usage_percentage, 100),
    }

@app.get("/api/admin/upgrade")
def admin_upgrade(current_user: dict = Depends(get_current_user_from_token), target_username: str = Query(...)):
    """Admin endpoint to forcefully upgrade a user to enterprise."""
    if current_user.get("github_id") not in ADMIN_GITHUB_IDS:
        raise HTTPException(status_code=403, detail="Forbidden: Admins only")
        
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username ILIKE %s", (target_username,))
                row = cur.fetchone()
                if not row:
                    return {"status": "error", "message": f"User {target_username} not found"}
                
                user_id = row[0]
                cur.execute(
                    """
                    INSERT INTO subscriptions (owner_type, user_owner_id, plan_type, status)
                    VALUES ('user', %s, 'enterprise', 'active')
                    ON CONFLICT (user_owner_id) 
                    DO UPDATE SET plan_type = 'enterprise', status = 'active'
                    """,
                    (user_id,)
                )
                conn.commit()
                return {"status": "success", "message": f"{target_username} successfully upgraded to ENTERPRISE!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_config():
    return {"saas_mode": is_saas_mode()}

@app.get("/api/admin/expire")
def admin_expire(github_id: int, current_user: dict = Depends(get_current_user_from_token)):
    """Admin endpoint to forcefully expire a user's subscription for testing."""
    if current_user.get("github_id") not in ADMIN_GITHUB_IDS:
        raise HTTPException(status_code=403, detail="Forbidden: Admins only")
        
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE github_id = %s", (github_id,))
                row = cur.fetchone()
                if not row:
                    return {"status": "error", "message": "User not found"}
                
                user_id = row[0]
                cur.execute(
                    """
                    UPDATE subscriptions 
                    SET expires_at = NOW() - INTERVAL '1 day', status = 'expired'
                    WHERE user_owner_id = %s
                    """,
                    (user_id,)
                )
                conn.commit()
                return {"status": "success", "message": f"User {github_id} successfully expired!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/impact/{symbol}")
def get_impact(
    symbol: str,
    depth: int = Query(3, ge=1, le=5),
    file_filter: str = Query(None, alias="file"),
    project_path: str = Query(None),
    current_user: dict = Depends(require_active_subscription)
):
    check_rate_limit(f"impact_{current_user['user_id']}", 20, 60)
    
    target_dir = project_path or os.getenv("TARGET_CODE_DIR", os.getcwd())
    target_dir = os.path.abspath(target_dir)
    
    allowed_base = os.path.abspath(os.getenv("TARGET_CODE_DIR", os.getcwd()))
    if not target_dir.startswith(allowed_base):
        raise HTTPException(status_code=403, detail="Path traversal detected. Access denied.")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Get project_id
                cur.execute("SELECT id FROM projects WHERE repo_url = %s", (target_dir,))
                proj = cur.fetchone()
                if not proj:
                    # Fallback: check by folder name
                    proj_name = os.path.basename(target_dir)
                    cur.execute("SELECT id FROM projects WHERE name = %s", (proj_name,))
                    proj = cur.fetchone()
                    if not proj:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Project not found for path '{target_dir}'. Please index it first."
                        )
                project_id = proj[0]
                
                # Find target symbol
                if file_filter:
                    escaped_filter = file_filter.replace("%", "\\%").replace("_", "\\_")
                    cur.execute(
                        """
                        SELECT s.id, s.name, s.file_path, s.start_line 
                        FROM symbols s 
                        LEFT JOIN (SELECT resolved_symbol_id, COUNT(*) as call_count FROM calls GROUP BY resolved_symbol_id) c 
                          ON s.id = c.resolved_symbol_id 
                        WHERE s.name = %s AND s.project_id = %s AND s.file_path LIKE %s 
                        ORDER BY COALESCE(c.call_count, 0) DESC, s.start_line ASC 
                        LIMIT 1
                        """,
                        (symbol, project_id, f"%{escaped_filter}%")
                    )
                else:
                    cur.execute(
                        """
                        SELECT s.id, s.name, s.file_path, s.start_line 
                        FROM symbols s 
                        LEFT JOIN (SELECT resolved_symbol_id, COUNT(*) as call_count FROM calls GROUP BY resolved_symbol_id) c 
                          ON s.id = c.resolved_symbol_id 
                        WHERE s.name = %s AND s.project_id = %s 
                        ORDER BY COALESCE(c.call_count, 0) DESC, s.start_line ASC 
                        LIMIT 1
                        """,
                        (symbol, project_id)
                    )
                target = cur.fetchone()
                if not target:
                    raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found in the index.")
                
                target_id, real_name, target_file, target_start_line = target
                
                # Recursive CTE query with Cycle Guard
                query = """
                WITH RECURSIVE impact_chain AS (
                    SELECT s.name AS source, s.file_path, c.line_number, 1 AS depth, target_sym.name AS target, c.source_symbol_id AS source_id,
                           ARRAY[c.source_symbol_id] AS path,
                           FALSE AS cycle
                    FROM calls c
                    JOIN symbols s ON c.source_symbol_id = s.id
                    JOIN symbols target_sym ON c.resolved_symbol_id = target_sym.id
                    WHERE c.resolved_symbol_id = %s
                    UNION ALL
                    SELECT s.name, s.file_path, c.line_number, ic.depth + 1, ic.source, c.source_symbol_id,
                           ic.path || c.source_symbol_id,
                           c.source_symbol_id = ANY(ic.path)
                    FROM impact_chain ic
                    JOIN calls c ON c.resolved_symbol_id = ic.source_id
                    JOIN symbols s ON c.source_symbol_id = s.id
                    WHERE ic.depth < %s + 1 AND NOT ic.cycle
                )
                SELECT DISTINCT source, file_path, line_number, depth, target
                FROM impact_chain WHERE NOT cycle ORDER BY depth ASC, file_path;
                """
                cur.execute(query, (target_id, depth))
                results = cur.fetchall()
                
                # Format visualizer nodes and edges response
                target_full_path = f"{target_dir}/{target_file}".replace("\\", "/") if target_file else ""
                target_start_line = target_start_line or 1
                target_code_ctx = get_code_context(target_full_path, target_start_line)
                
                nodes = [{
                    "id": real_name,
                    "label": real_name,
                    "group": 0,
                    "path": target_full_path,
                    "line": target_start_line,
                    "code_context": target_code_ctx
                }]
                edges = []
                
                seen_nodes = {real_name}
                for source, path, line, d, target_node in results:
                    full_path = f"{target_dir}/{path}".replace("\\", "/") if path else ""
                    code_ctx = get_code_context(full_path, line)
                    
                    if source not in seen_nodes:
                        nodes.append({
                            "id": source,
                            "label": source,
                            "group": d,
                            "path": full_path,
                            "line": line,
                            "code_context": code_ctx
                        })
                        seen_nodes.add(source)
                    
                    if target_node not in seen_nodes:
                        nodes.append({
                            "id": target_node,
                            "label": target_node,
                            "group": max(0, d - 1),
                            "path": full_path,
                            "line": line,
                            "code_context": code_ctx
                        })
                        seen_nodes.add(target_node)
                    
                    edges.append({
                        "from": source,
                        "to": target_node
                    })
                
                return {
                    "target": {
                        "name": real_name,
                        "file_path": target_file,
                        "line": target_start_line
                    },
                    "nodes": nodes,
                    "edges": edges,
                    "summary": {
                        "total_impacted": len(seen_nodes) - 1,
                        "max_depth_explored": depth
                    }
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Header
from n3mo.api.webhook_handler import revoke_github_installation

@app.post("/internal/sweep-expired")
def sweep_expired_subscriptions(authorization: str = Header(None)):
    """Find all expired subscriptions and revoke their GitHub Apps."""
    sweep_token = os.getenv("INTERNAL_SWEEP_TOKEN")
    if not sweep_token or authorization != f"Bearer {sweep_token}":
        raise HTTPException(status_code=401, detail="Unauthorized sweep request")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, o.installation_id 
                    FROM subscriptions s
                    JOIN users u ON s.user_owner_id = u.id
                    LEFT JOIN organizations o ON o.owner_user_id = u.id
                    WHERE s.status = 'expired' AND o.installation_id IS NOT NULL
                    """
                )
                rows = cur.fetchall()
                count = 0
                for row in rows:
                    installation_id = str(row[1])
                    if revoke_github_installation(installation_id):
                        count += 1
                        # Nullify installation_id to prevent retries
                        cur.execute("UPDATE organizations SET installation_id = NULL WHERE installation_id = %s", (row[1],))
                conn.commit()
                return {"status": "success", "revoked_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if not os.getenv("VERCEL"):
    if os.path.exists("public"):
        app.mount("/", StaticFiles(directory="public", html=True), name="static")
    elif os.path.exists("frontend"):
        app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

def start_server(host="127.0.0.1", port=8000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()
