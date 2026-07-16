# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import logging
import json

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from n3mo.core.run_indexer import run_indexer_for_path
from n3mo.core.database import get_connection, release_connection
from n3mo.cli.cli import get_code_context
from n3mo.api.webhook_handler import router as webhook_router
from n3mo.api.auth import router as auth_router
from n3mo.api.marketplace import router as marketplace_router
from n3mo.api.admin import router as admin_router
from n3mo.api.auth import get_current_user_from_token
from fastapi import Depends
from n3mo.saas_db import get_subscription, get_user_by_id, get_user_by_github_id, update_subscription
import razorpay  # type: ignore
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
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_123")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "secret")

class IndexRequest(BaseModel):
    target_dir: str

@app.get("/health")
def health():
    return {"status": "healthy", "service": "n3mo-api"}

@app.post("/index")
def trigger_indexing(req: IndexRequest):
    target_dir = os.path.abspath(req.target_dir)
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=400, detail=f"Directory '{target_dir}' does not exist.")
    
    success, summary = run_indexer_for_path(target_dir)
    if not success:
        raise HTTPException(status_code=500, detail=summary)
    
    return {"status": "success", "summary": summary}



def get_usd_to_inr_rate() -> float:
    """Fetch live USD to INR conversion rate, fallback to 84.0 if API fails."""
    try:
        import urllib.request
        req = urllib.request.Request("https://open.er-api.com/v6/latest/USD", headers={"User-Agent": "N3MO-SaaS/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return float(data["rates"]["INR"])
    except Exception as e:
        logging.warning(f"Failed to fetch live USD-INR rate, falling back to 95.33: {e}")
        return 95.33

# Live Razorpay Plan IDs (USD + INR Bulk)
PLAN_MAPPINGS = {
    "starter_monthly_usd": "plan_TCWjmSxZIjA6YW",
    "starter_yearly_usd": "plan_TCWjmiMDyhhoYa",
    "pro_monthly_usd": "plan_TCWjmy2f2uHREd",
    "pro_yearly_usd": "plan_TCWjnG1UvC58JH",
    "team_monthly_usd": "plan_TCWjnflH7Oh6Us",
    "team_quarterly_usd": "plan_TCWjo1JFYPODeX",
    "starter_yearly_inr": "plan_TCWjoFChjPJ2VN",
    "pro_yearly_inr": "plan_TCWjoTZpMjhzrr",
    "team_quarterly_inr": "plan_TCWjooApEUVnkn",
}

@app.post("/api/create-subscription")
def create_subscription(github_id: str, country: str = "US", discount: str = "", plan_type: str = "pro", billing_cycle: str = "monthly"):
    """
    Generate a Razorpay checkout subscription for the specified plan and billing cycle.
    billing_cycle can be 'monthly' or 'bulk' (which maps to yearly for starter/pro, quarterly for team)
    """
    if not github_id:
        raise HTTPException(status_code=400, detail="github_id is required")
        
    try:
        key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_123").strip()
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "secret").strip()
        client = razorpay.Client(auth=(key_id, key_secret))
        
        prices_usd_monthly = {"starter": 10, "pro": 49, "team": 199}
        prices_usd_bulk = {"starter": 102, "pro": 558, "team": 537}
        
        amount_usd_raw = prices_usd_bulk.get(plan_type, 558) if billing_cycle == "bulk" else prices_usd_monthly.get(plan_type, 49)

        if country.upper() == "IN":
            live_rate = get_usd_to_inr_rate()
            amount = int(amount_usd_raw * live_rate * 100)
            currency = "INR"
        else:
            amount = int(amount_usd_raw * 100)
            currency = "USD"
        
        # Apply dynamic discount logic
        if discount:
            from n3mo.saas_db import validate_and_use_discount_code
            discount_data = validate_and_use_discount_code(discount)
            
            if discount_data:
                discount_percentage = discount_data["discount_percentage"]
                
                if discount_percentage == 100:
                    from n3mo.saas_db import update_subscription, get_user_by_github_id
                    from datetime import datetime, timedelta, timezone
                    user_db = get_user_by_github_id(int(github_id))
                    if user_db:
                        expires_at = datetime.now(timezone.utc) + timedelta(days=365 if billing_cycle == 'bulk' else 30)
                        update_subscription(str(user_db["id"]), "user", plan_type, "active", expires_at=expires_at)
                    
                    return {
                        "checkout_url": "", 
                        "order_id": "",
                        "key_id": key_id,
                        "free_upgrade": True
                    }
                else:
                    # Apply percentage discount
                    amount = int(amount * (1 - discount_percentage / 100))
            else:
                # Invalid or expired discount code
                pass
            
        # Create Order
        order_payload = {
            "amount": amount,
            "currency": currency,
            "receipt": f"receipt_{github_id}_{plan_type}",
            "notes": {
                "github_id": github_id,
                "plan_type": plan_type,
                "billing_cycle": billing_cycle
            }
        }
        
        order = client.order.create(order_payload)
        
        return {
            "checkout_url": "", 
            "order_id": order["id"],
            "key_id": key_id
        }
    except Exception as e:
        logging.error(f"Error creating Razorpay subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    github_id: str
    plan_type: str = "pro"

@app.post("/api/verify-payment")
def verify_payment(req: VerifyPaymentRequest):
    try:
        key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_123").strip()
        key_secret = os.getenv("RAZORPAY_KEY_SECRET", "secret").strip()
        client = razorpay.Client(auth=(key_id, key_secret))
        params_dict = {
            'razorpay_order_id': req.razorpay_order_id,
            'razorpay_payment_id': req.razorpay_payment_id,
            'razorpay_signature': req.razorpay_signature
        }
        
        # Verify signature
        client.utility.verify_payment_signature(params_dict)
        
        # If successful, upgrade the user
        user_db = get_user_by_github_id(int(req.github_id))
        if user_db:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            update_subscription(str(user_db["id"]), "user", req.plan_type, "active", expires_at=expires_at)
            return {"status": "success", "message": f"Payment verified, upgraded to {req.plan_type.upper()}."}
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    except Exception as e:
        logging.error(f"Error verifying payment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/user/dashboard-data")
def get_dashboard_data(current_user: dict = Depends(get_current_user_from_token)):
    """Fetch all data needed for the user dashboard."""
    user_id = current_user["user_id"]
    user_db = get_user_by_id(user_id)
    if not user_db:
        raise HTTPException(status_code=401, detail="User not found in database. Please re-authenticate.")
        
    subscription = get_subscription(user_id, "user")
    
    if current_user["username"].lower() == "rajx-dev":
        subscription = {"plan_type": "enterprise", "status": "active", "expires_at": None, "created_at": None}
    
    return {
        "status": "success",
        "user": {
            "username": current_user["username"],
            "github_id": user_db.get("github_id"),
            "avatar_url": user_db.get("avatar_url")
        },
        "subscription": subscription,
        "webhook_secret": user_db.get("webhook_secret")
    }

@app.get("/api/admin/upgrade")
def admin_upgrade():
    """Secret endpoint to forcefully upgrade RajX-dev to enterprise."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username ILIKE 'RajX-dev'")
            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "User RajX-dev not found"}
            
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
            return {"status": "success", "message": "RajX-dev successfully upgraded to ENTERPRISE!"}
    finally:
        release_connection(conn)

@app.get("/api/config")
def get_config():
    is_saas = os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")
    return {"saas_mode": is_saas}

@app.get("/api/admin/expire")
def admin_expire(github_id: int):
    """Secret endpoint to forcefully expire a user's subscription for testing."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE github_id = %s", (github_id,))
            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "User not found"}
            
            user_id = row[0]
            cur.execute(
                """
                UPDATE subscriptions 
                SET expires_at = NOW() - INTERVAL '1 day'
                WHERE user_owner_id = %s
                """,
                (user_id,)
            )
            conn.commit()
            return {"status": "success", "message": f"User {github_id} successfully expired!"}
    finally:
        release_connection(conn)

@app.get("/impact/{symbol}")
def get_impact(
    symbol: str,
    depth: int = Query(3, ge=1, le=5),
    file_filter: str = Query(None, alias="file"),
    project_path: str = Query(None)
):
    target_dir = project_path or os.getenv("TARGET_CODE_DIR", os.getcwd())
    target_dir = os.path.abspath(target_dir)
    
    conn = get_connection()
    try:
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
                    (symbol, project_id, f"%{file_filter}%")
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
    finally:
        release_connection(conn)

def start_server(host="127.0.0.1", port=8000):
    if not os.getenv("VERCEL"):
        if os.path.exists("public"):
            app.mount("/", StaticFiles(directory="public", html=True), name="static")
        elif os.path.exists("frontend"):
            app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()
