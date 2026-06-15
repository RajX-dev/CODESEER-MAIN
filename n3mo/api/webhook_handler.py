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
import shutil
import urllib.request
import urllib.error
import json
from fastapi import APIRouter, FastAPI, Request, Header, HTTPException

from n3mo.run_indexer import run_indexer_for_path
from n3mo.database import get_connection, release_connection
from n3mo.crawler import crawl_directory

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
        return f"### ◈ N3MO Pull Request Impact Analysis\n\n✓ **Safe to change:** No active symbols were modified/affected in this Pull Request."

    sorted_symbols = sorted(merged_impacts.items(), key=lambda x: (x[1]["status"], x[0]))
    
    markdown = f"### ◈ N3MO Pull Request Impact Analysis\n\n"
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
            status_badge = " 🟠 `Modified`"
        elif status == "Added":
            status_badge = " 🟢 `Added`"
        elif status == "Deleted":
            status_badge = " 🔴 `Deleted`"
            
        markdown += f"| `{file_path}` | `{name}` | {status_badge} | {direct_count} | {total_count} | [View Details](#{name.lower()}) |\n"
        
        # Details section
        details = f"<a name=\"{name.lower()}\"></a>\n"
        details += f"#### ◉ `{name}` ({status})\n"
        details += f"*   **Location:** `{file_path}:{line}`\n"
        if not callers:
            details += f"*   **Blast Radius:** 0 callers (safe to change, no dependencies found).\n"
        else:
            direct_callers = [c for c in callers if c["depth"] == 1]
            ripple_callers = [c for c in callers if c["depth"] > 1]
            
            if direct_callers:
                details += f"*   **Direct Callers:**\n"
                for c in direct_callers:
                    details += f"    *   `{c['source']}` (`{c['file_path']}:{c['line']}`)\n"
            if ripple_callers:
                details += f"*   **Ripple Effects:**\n"
                for c in sorted(ripple_callers, key=lambda x: x["depth"]):
                    indent = "  " * (c["depth"] - 1)
                    details += f"    *{indent}─▸ `{c['source']}` (`{c['file_path']}:{c['line']}`)\n"
        details_sections.append(details)
        
    markdown += "\n---\n\n"
    markdown += "### 🔍 Impact Details\n\n"
    markdown += "\n".join(details_sections)
    return markdown

def get_github_app_installation_token(app_id: str, private_key_env: str, private_key_path: str, installation_id: str) -> str:
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
        "iss": int(app_id)
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

def post_github_comment(repo_name: str, pr_number: int, body_markdown: str, installation_id: str = None):
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    
    app_id = os.getenv("GITHUB_APP_ID")
    private_key_env = os.getenv("GITHUB_APP_PRIVATE_KEY")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    
    if not token and app_id and (private_key_env or private_key_path) and installation_id:
        logger.info("Authenticating as GitHub App...")
        token = get_github_app_installation_token(app_id, private_key_env, private_key_path, installation_id)
        
    if not token:
        logger.warning("⚠️ No GITHUB_TOKEN or GITHUB_APP credentials found. Printing report to stdout.")
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
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    if not x_github_event:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    # Verify signature if secret is configured
    if GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
        parts = x_hub_signature_256.split("=")
        if len(parts) != 2 or parts[0] != "sha256":
            raise HTTPException(status_code=400, detail="Invalid signature format")
        body = await request.body()
        expected = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, parts[1]):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    logger.info(f"Received GitHub event: {x_github_event}")

    if x_github_event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize"]:
            return handle_pull_request(payload)

    return {"message": f"Event '{x_github_event}' ignored"}

def handle_pull_request(payload: dict) -> dict:
    pr_number = payload.get("number")
    repo_name = payload.get("repository", {}).get("full_name")
    clone_url = payload.get("repository", {}).get("clone_url")
    base_sha = payload.get("pull_request", {}).get("base", {}).get("sha")
    head_sha = payload.get("pull_request", {}).get("head", {}).get("sha")
    installation_id = payload.get("installation", {}).get("id")

    logger.info(f"Analyzing PR #{pr_number} for {repo_name} (from {base_sha} to {head_sha})")

    # 1. Checkout repository to get current files
    repo_dir = checkout_repo(clone_url, repo_name, head_sha)

    # 2. Check 15k lines of code limit
    total_lines = calculate_repo_loc(repo_dir)
    is_licensed = bool(N3MO_LICENSE_KEY) or N3MO_SUBSCRIPTION_ACTIVE
    
    if total_lines > 15000 and not is_licensed:
        logger.warning(f"Free tier limit exceeded for {repo_name}: {total_lines} LOC")
        warning_msg = (
            f"### ⚠️ N3MO Tier Limit Reached\n\n"
            f"This repository contains **{total_lines:,} lines of code**, which exceeds N3MO's free tier limit of **15,000 lines**.\n\n"
            f"To enable PR checks on this repository, please:\n"
            f"1. **Upgrade your plan** on our SaaS platform to activate your subscription, or\n"
            f"2. Configure your own **Self-Hosted N3MO edition** on private infrastructure.\n\n"
            f"*Already upgraded? Configure the `N3MO_LICENSE_KEY` environment variable in your app deployment.*"
        )
        post_github_comment(repo_name, pr_number, warning_msg, installation_id)
        return {
            "status": "limit_exceeded",
            "loc": total_lines,
            "message": "Repository exceeds free tier limit of 15,000 lines."
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
