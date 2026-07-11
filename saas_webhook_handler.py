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

# Helper functions
def get_workspace_dir(repo_name: str) -> str:
    workspace_root = os.getenv("N3MO_WORKSPACE_DIR", os.path.join(os.getcwd(), "n3mo_workspaces"))
    return os.path.abspath(os.path.join(workspace_root, repo_name.replace("/", "_")))

def calculate_repo_loc(repo_dir: str) -> int:
    files = crawl_directory(repo_dir)
    total_lines = 0
    for fpath in files:
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                total_lines += sum(1 for _ in f)
        except Exception:
            pass
    return total_lines

def checkout_repo(clone_url: str, repo_name: str, sha: str) -> str:
    repo_dir = get_workspace_dir(repo_name)
    os.makedirs(os.path.dirname(repo_dir), exist_ok=True)
    if not os.path.exists(repo_dir):
        logger.info(f"Cloning {clone_url} to {repo_dir}...")
        subprocess.run(["git", "clone", clone_url, repo_dir], check=True)
    else:
        logger.info(f"Fetching updates for {repo_name}...")
        subprocess.run(["git", "fetch", "origin"], cwd=repo_dir, check=True)
        
    logger.info(f"Checking out {sha}...")
    subprocess.run(["git", "checkout", "-f", sha], cwd=repo_dir, check=True)
    return repo_dir

def get_changed_files(repo_dir: str, base_sha: str, head_sha: str) -> list:
    res = subprocess.run(
        ["git", "diff", "--name-only", base_sha, head_sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True
    )
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]

def get_project_id(repo_dir: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM projects WHERE repo_url = %s", (repo_dir,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        release_connection(conn)

def get_impact_for_changed_files(project_id, changed_files: list) -> dict:
    if not project_id or not changed_files:
        return {}
        
    conn = get_connection()
    impacts = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, file_path, start_line
                FROM symbols
                WHERE project_id = %s AND file_path = ANY(%s)
                """,
                (project_id, changed_files)
            )
            symbols = cur.fetchall()
            
            for sym_id, name, file_path, start_line in symbols:
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
                    WHERE ic.depth < 4 AND NOT ic.cycle
                )
                SELECT DISTINCT source, file_path, line_number, depth, target
                FROM impact_chain WHERE NOT cycle ORDER BY depth ASC, file_path;
                """
                cur.execute(query, (sym_id,))
                callers = cur.fetchall()
                impacts[name] = {
                    "file_path": file_path,
                    "line": start_line,
                    "callers": [{"source": c[0], "file_path": c[1], "line": c[2], "depth": c[3]} for c in callers]
                }
    finally:
        release_connection(conn)
    return impacts

def merge_impacts(base_impacts: dict, head_impacts: dict) -> dict:
    merged = {}
    all_symbols = set(base_impacts.keys()) | set(head_impacts.keys())
    for sym in all_symbols:
        in_base = sym in base_impacts
        in_head = sym in head_impacts
        if in_base and in_head:
            status = "Modified"
            data = head_impacts[sym]
        elif in_head:
            status = "Added"
            data = head_impacts[sym]
        else:
            status = "Deleted"
            data = base_impacts[sym]
            
        merged[sym] = {
            "status": status,
            "file_path": data["file_path"],
            "line": data["line"],
            "callers": data["callers"]
        }
    return merged

def format_impact_markdown(merged_impacts: dict, repo_name: str, pr_number: int, total_lines: int) -> str:
    if not merged_impacts:
        return "### Γùê N3MO Pull Request Impact Analysis\n\nΓ£ô **Safe to change:** No active symbols were modified/affected in this Pull Request."

    sorted_symbols = sorted(merged_impacts.items(), key=lambda x: (x[1]["status"], x[0]))
    
    markdown = "### Γùê N3MO Pull Request Impact Analysis\n\n"
    markdown += f"Analyzed {total_lines:,} lines of code. Below is the blast radius report for changes in PR #{pr_number}.\n\n"
    markdown += "| File | Symbol | Status | Direct Callers | Total Impacted | Details |\n"
    markdown += "| :--- | :--- | :--- | :---: | :---: | :--- |\n"
    
    details_sections = []
    
    for name, data in sorted_symbols:
        status = data["status"]
        file_path = data["file_path"]
        line = data["line"]
        callers = data["callers"]
        
        direct_count = len([c for c in callers if c["depth"] == 1])
        total_count = len(callers)
        
        status_badge = f" `{status}`"
        if status == "Modified":
            status_badge = " ≡ƒƒá `Modified`"
        elif status == "Added":
            status_badge = " ≡ƒƒó `Added`"
        elif status == "Deleted":
            status_badge = " ≡ƒö┤ `Deleted`"
            
        markdown += f"| `{file_path}` | `{name}` | {status_badge} | {direct_count} | {total_count} | [View Details](#{name.lower()}) |\n"
        
        # Details section
        details = f"<a name=\"{name.lower()}\"></a>\n"
        details += f"#### Γùë `{name}` ({status})\n"
        details += f"*   **Location:** `{file_path}:{line}`\n"
        if not callers:
            details += "*   **Blast Radius:** 0 callers (safe to change, no dependencies found).\n"
        else:
            direct_callers = [c for c in callers if c["depth"] == 1]
            ripple_callers = [c for c in callers if c["depth"] > 1]
            
            if direct_callers:
                details += "*   **Direct Callers:**\n"
                for c in direct_callers:
                    details += f"    *   `{c['source']}` (`{c['file_path']}:{c['line']}`)\n"
            if ripple_callers:
                details += f"\n<details>\n<summary><b>View {len(ripple_callers)} Ripple Effects</b></summary>\n\n"
                for c in sorted(ripple_callers, key=lambda x: x["depth"]):
                    indent = "  " * (c["depth"] - 1)
                    details += f"{indent}* ΓöÇΓû╕ `{c['source']}` (`{c['file_path']}:{c['line']}`)\n"
                details += "\n</details>\n"
        details_sections.append(details)
        
    markdown += "\n---\n\n"
    markdown += "### ≡ƒöì Impact Details\n\n"
    markdown += "\n".join(details_sections)
    return markdown

def get_github_app_installation_token(
    app_id: str | None,
    private_key_env: str | None,
    private_key_path: str | None,
    installation_id: str | int | None
) -> str:
    if not app_id:
        raise HTTPException(status_code=500, detail="Missing GITHUB_APP_ID")
        
    try:
        import jwt
        import time
    except ImportError:
        logger.error("jwt package not found. Please install PyJWT and cryptography.")
        raise HTTPException(status_code=500, detail="PyJWT and cryptography packages are required for GitHub App authentication")
        
    private_key = private_key_env
    if not private_key and private_key_path:
        if os.path.exists(private_key_path):
            with open(private_key_path, "r") as f:
                private_key = f.read()
                
    if not private_key:
        raise HTTPException(status_code=500, detail="GitHub App private key is empty or not found")
        
    private_key = private_key.replace("\\n", "\n")
    
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": str(app_id)
    }
    
    token_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    
    if not installation_id:
        raise HTTPException(status_code=400, detail="Missing installation ID for App token request")
        
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token_jwt}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "N3MO-Impact-Tracker"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("token")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        logger.error(f"Failed to get App installation token: {e.code} - {err_msg}")
        raise HTTPException(status_code=e.code, detail=f"GitHub App Token Error: {err_msg}")

def delete_github_app_installation(
    app_id: str | None,
    private_key_env: str | None,
    private_key_path: str | None,
    installation_id: str | int | None
) -> bool:
    if not app_id or not installation_id:
        return False
        
    try:
        import jwt
        import time
    except ImportError:
        return False
        
    private_key = private_key_env
    if not private_key and private_key_path:
        if os.path.exists(private_key_path):
            with open(private_key_path, "r") as f:
                private_key = f.read()
                
    if not private_key:
        return False
        
    private_key = private_key.replace("\\n", "\n")
    
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": str(app_id)
    }
    
    token_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    
    url = f"https://api.github.com/app/installations/{installation_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token_jwt}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "N3MO-SaaS"
        },
        method="DELETE"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            return True
    except Exception as e:
        logger.error(f"Failed to delete App installation {installation_id}: {e}")
        return False

def post_github_comment(
    repo_name: str,
    pr_number: int,
    body_markdown: str,
    installation_id: str | int | None = None
) -> dict:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    
    app_id = os.getenv("GITHUB_APP_ID")
    private_key_env = os.getenv("GITHUB_APP_PRIVATE_KEY")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH") or os.getenv("GITHUB_PRIVATE_KEY_PATH")
    
    if not token and app_id and (private_key_env or private_key_path) and installation_id:
        logger.info("Authenticating as GitHub App...")
        token = get_github_app_installation_token(app_id, private_key_env, private_key_path, installation_id)
        
    if not token:
        logger.warning("ΓÜá∩╕Å No GITHUB_TOKEN or GITHUB_APP credentials found. Printing report to stdout.")
        print("\n--- REPORT COMMENT ---\n")
        print(body_markdown)
        print("\n----------------------\n")
        return {"status": "printed_locally", "reason": "no_credentials"}
        
    url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
    req = urllib.request.Request(
        url,
        data=json.dumps({"body": body_markdown}).encode("utf-8"),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "N3MO-Impact-Tracker"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            logger.info(f"Successfully posted comment to PR #{pr_number}")
            return {"status": "posted", "comment_id": data.get("id")}

    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        logger.error(f"Failed to post comment: {e.code} - {err_msg}")
        raise HTTPException(status_code=e.code, detail=f"GitHub API Error: {err_msg}")

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
                    
                # Check subscription expiration
                from n3mo.saas_db import get_subscription
                sub = get_subscription(str(user_db.get("id")), "user")
                if sub.get("status") == "expired":
                    installation = payload.get("installation")
                    installation_id = installation.get("id") if isinstance(installation, dict) else None
                    if installation_id:
                        app_id = os.getenv("GITHUB_APP_ID")
                        private_key_env = os.getenv("GITHUB_APP_PRIVATE_KEY")
                        private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH") or os.getenv("GITHUB_PRIVATE_KEY_PATH")
                        delete_github_app_installation(app_id, private_key_env, private_key_path, installation_id)
                        logger.warning(f"Subscription expired for user {user_db.get('id')}. Revoked GitHub App installation {installation_id}.")
                    return {"status": "error", "message": "Subscription expired. GitHub webhook token revoked."}

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

def enforce_repo_limits(user_id: str, repo_full_name: str, is_private: bool = True) -> bool:
    from n3mo.database import get_connection, release_connection
    from n3mo.saas_db import get_subscription
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if repo already registered
            cur.execute("SELECT id FROM saas_repo_tracking WHERE user_owner_id = %s AND repo_full_name = %s", (user_id, repo_full_name))
            if cur.fetchone():
                return True
                
            # Count connected repos
            cur.execute("SELECT count(id) FROM saas_repo_tracking WHERE user_owner_id = %s", (user_id,))
            repo_count = cur.fetchone()[0]
            
            sub = get_subscription(user_id, "user")
            plan_type = sub.get("plan_type", "free")
            status = sub.get("status", "active")
            
            limit = 3  # Starter/Free limit
            if not is_private:
                limit = 999999
            else:
                if plan_type == "pro" and status == "active":
                    limit = 5
                elif plan_type == "team" and status == "active":
                    limit = 8
                elif plan_type == "enterprise" and status == "active":
                    limit = 999999
                
            if repo_count >= limit:
                return False
                
            # Register new repo
            cur.execute(
                "INSERT INTO saas_repo_tracking (user_owner_id, repo_full_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, repo_full_name)
            )
            conn.commit()
            return True
    finally:
        release_connection(conn)

def handle_pull_request(payload: dict) -> dict:
    pr_number_raw = payload.get("number")
    if pr_number_raw is None:
        logger.error("Missing PR number in payload")
        return {"status": "error", "message": "Missing pull request number."}
    pr_number = int(pr_number_raw)
    
    repo_name = payload.get("repository", {}).get("full_name")
    clone_url = payload.get("repository", {}).get("clone_url")
    base_sha = payload.get("pull_request", {}).get("base", {}).get("sha")
    head_sha = payload.get("pull_request", {}).get("head", {}).get("sha")
    
    installation = payload.get("installation")
    installation_id = installation.get("id") if isinstance(installation, dict) else None


    logger.info(f"Analyzing PR #{pr_number} for {repo_name} (from {base_sha} to {head_sha})")
    
    # Verify Repository SaaS Limits if SaaS Mode
    is_saas = os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")
    if is_saas:
        repo_owner_name = payload.get("repository", {}).get("owner", {}).get("login")
        is_private = payload.get("repository", {}).get("private", True)
        if repo_owner_name:
            from n3mo.saas_db import get_user_by_username
            user_db = get_user_by_username(repo_owner_name)
            if user_db:
                user_id = str(user_db.get("id"))
                if not enforce_repo_limits(user_id, repo_name, is_private):
                    logger.warning(f"Repo limit reached for user {repo_owner_name}")
                    if installation_id:
                        # Post comment explaining repo limit
                        github_token = user_db.get("github_token") or os.getenv("GITHUB_TOKEN")
                        if github_token:
                            comment_url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
                            comment_body = "⚠️ **N3MO Analysis Aborted**\n\nYour account has reached its maximum repository limit for the current plan. Please upgrade to Pro or Team on your dashboard to analyze this repository."
                            post_github_comment(comment_url, comment_body, github_token)
                    return {"status": "error", "message": "Repository limit reached"}

    # 1. Checkout repository to get current files
    repo_dir = checkout_repo(clone_url, repo_name, head_sha)

    # 2. Check limits based on self-hosted license or SaaS subscription
    license_key = os.getenv("N3MO_LICENSE_KEY")
    license_info = verify_license_key(license_key) if license_key else {"valid": False, "plan_type": "free", "max_loc": 150000}
    
    is_saas = os.getenv("N3MO_SAAS_MODE", "false").lower() in ("true", "1", "yes")
    
    max_loc = 150000
    plan_name = "Starter Plan"
    
    if license_info["valid"]:
        max_loc_val = license_info["max_loc"]
        max_loc = max_loc_val if isinstance(max_loc_val, int) else 150000
        plan_name = f"Self-Hosted {str(license_info['plan_type']).capitalize()}"
    elif is_saas:
        # Fallback to SaaS database subscription lookup
        repo_owner_name = payload.get("repository", {}).get("owner", {}).get("login")
        repo_owner_id = payload.get("repository", {}).get("owner", {}).get("id")
        repo_owner_type = payload.get("repository", {}).get("owner", {}).get("type") # "User" or "Organization"
        
        db_owner_id = None
        if repo_owner_id:
            if repo_owner_type == "User":
                user_rec = upsert_user(github_id=repo_owner_id, username=repo_owner_name)
                db_owner_id = user_rec.get("id")
                owner_cat = "user"
            elif repo_owner_type == "Organization":
                org_rec = upsert_organization(github_id=repo_owner_id, name=repo_owner_name)
                db_owner_id = org_rec.get("id")
                owner_cat = "organization"
                
            if db_owner_id:
                sub = get_subscription(db_owner_id, owner_cat)
                if sub.get("status") == "active":
                    plan_type_str = str(sub.get("plan_type") or "free")
                    plan_name = f"SaaS {plan_type_str.capitalize()}"
                    if sub.get("plan_type") == "enterprise":
                        max_loc = -1 # Unlimited
                    elif sub.get("plan_type") == "team":
                        max_loc = 1000000 # 1M LOC for Team
                    elif sub.get("plan_type") == "pro":
                        max_loc = 100000 # 100k LOC for Pro
    else:
        # Self-hosted without a valid license key -> Free and Unlimited
        max_loc = -1
        plan_name = "Self-Hosted Community Edition"
    
    is_private = payload.get("repository", {}).get("private", True)
    if not is_private:
        max_loc = -1
        plan_name = plan_name + " (Open Source)"
    
    total_lines = calculate_repo_loc(repo_dir)
    # Check limit if max_loc is positive (not -1 for unlimited)
    if max_loc > 0 and total_lines > max_loc:
        logger.warning(f"LOC limit exceeded for {repo_name}: {total_lines} LOC (Limit: {max_loc} for {plan_name})")
        warning_msg = (
            f"###  N3MO Tier Limit Reached ({plan_name})\n\n"
            f"This repository contains **{total_lines:,} lines of code**, which exceeds N3MO's limit of **{max_loc:,} lines** for this plan.\n\n"
            f"To enable PR checks on this repository, please:\n"
            f"1. **Upgrade your plan** on our SaaS platform to activate a Pro or Enterprise subscription, or\n"
            f"2. Configure your own **Self-Hosted N3MO Enterprise edition** on your private infrastructure.\n\n"
            f"*Already upgraded? Configure your `N3MO_LICENSE_KEY` environment variable in your deployment.*"
        )
        post_github_comment(repo_name, pr_number, warning_msg, installation_id)
        return {
            "status": "limit_exceeded",
            "loc": total_lines,
            "message": f"Repository exceeds plan limit of {max_loc} lines."
        }

    # 3. Get list of changed files
    try:
        changed_files = get_changed_files(repo_dir, base_sha, head_sha)
    except Exception as e:
        logger.error(f"Failed to get git diff: {e}")
        changed_files = []

    if not changed_files:
        logger.info(f"No changes detected in source files for PR #{pr_number}")
        report_md = format_impact_markdown({}, repo_name, pr_number, total_lines)
        post_github_comment(repo_name, pr_number, report_md, installation_id)
        return {"status": "processed", "changed_symbols_count": 0}

    # 4. Fetch impacts at base_sha
    try:
        checkout_repo(clone_url, repo_name, base_sha)
        run_indexer_for_path(repo_dir)
        project_id = get_project_id(repo_dir)
        base_impacts = get_impact_for_changed_files(project_id, changed_files)
    except Exception as e:
        logger.error(f"Failed base branch indexing: {e}")
        base_impacts = {}

    # 5. Fetch impacts at head_sha
    try:
        checkout_repo(clone_url, repo_name, head_sha)
        run_indexer_for_path(repo_dir)
        project_id = get_project_id(repo_dir)
        head_impacts = get_impact_for_changed_files(project_id, changed_files)
    except Exception as e:
        logger.error(f"Failed head branch indexing: {e}")
        head_impacts = {}

    # 6. Merge impacts and post report
    merged_impacts = merge_impacts(base_impacts, head_impacts)
    report_md = format_impact_markdown(merged_impacts, repo_name, pr_number, total_lines)
    
    result = post_github_comment(repo_name, pr_number, report_md, installation_id)
    
    return {
        "status": "processed",
        "changed_symbols_count": len(merged_impacts),
        "post_result": result
    }

# Standalone App for webhook_handler
app = FastAPI(
    title="N3MO GitHub App Webhook API",
    description="Listens to GitHub webhooks to run incremental impact analysis on Pull Requests.",
    version="0.1.0"
)
app.include_router(router)
