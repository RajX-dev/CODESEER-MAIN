import os
import sys
import logging
import subprocess
import urllib.request
import urllib.error
import json
import traceback
import re
import uuid

from n3mo.core.core_engine import (
    checkout_repo, 
    get_changed_files, 
    calculate_repo_loc, 
    get_project_id,
    get_impact_for_changed_files,
    merge_impacts,
    format_impact_markdown,
    post_github_comment
)
from n3mo.core.run_indexer import run_indexer_for_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("n3mo.worker")


def fetch_pr_details(repo_full_name: str, pr_number: str) -> dict:
    """Fetch PR metadata from the GitHub API."""
    github_pat = os.getenv("GITHUB_PAT")
    if not github_pat:
        raise ValueError("Missing GITHUB_PAT environment variable — cannot authenticate with GitHub API.")

    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {github_pat}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "N3MO-Worker"
        }
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise ValueError(f"GitHub API returned error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise ValueError(f"Failed to connect to GitHub API: {e.reason}")


def _get_plan_limits(plan_type: str, sub: dict = None) -> tuple[int, str]:
    """Return (max_loc, plan_name) for a given plan type based on subscription data."""
    if sub and sub.get("pricing_version") == "2":
        loc_limit = sub.get("loc_per_repo_limit")
        if loc_limit == -1:
            loc_limit = 99999999
        return (loc_limit or 0, f"SaaS {plan_type.capitalize()}")
    
    plan_map = {
        "enterprise": (-1, "SaaS Enterprise"),
        "team_pro": (500000, "SaaS Team Pro"),
        "team_basic": (200000, "SaaS Team Basic"),
        "pro": (100000, "SaaS Pro Plan"),
        "standard": (30000, "SaaS Standard Plan"),
        "none": (0, "SaaS None"),
    }
    return plan_map.get(plan_type, (0, "SaaS None"))


def main():
    target_repo = os.getenv("TARGET_REPO")
    pr_number = os.getenv("PR_NUMBER")
    user_id = os.getenv("USER_ID")
    installation_id = os.getenv("INSTALLATION_ID")
    
    if not target_repo or not pr_number:
        logger.error("Missing TARGET_REPO or PR_NUMBER in environment")
        sys.exit(1)
        
    if not re.match(r'^[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_\.]+$', target_repo):
        logger.error("Invalid TARGET_REPO format")
        sys.exit(1)
        
    if not re.match(r'^[0-9]+$', pr_number):
        logger.error("Invalid PR_NUMBER format")
        sys.exit(1)
        
    if user_id:
        if not re.match(r'^[0-9]+$', user_id):
            try:
                uuid.UUID(user_id)
            except ValueError:
                logger.error("Invalid USER_ID format")
                sys.exit(1)
                
    if installation_id and not re.match(r'^[0-9]+$', installation_id):
        logger.error("Invalid INSTALLATION_ID format")
        sys.exit(1)
    
    logger.info("🚀 N3MO CORE ENGINE WAKING UP")
    logger.info(f"Target Repository: {target_repo}")
    logger.info(f"Pull Request: #{pr_number}")
    logger.info(f"User ID: {user_id}")
    
    try:
        # 1. Fetch PR details
        logger.info("Fetching PR details from GitHub API...")
        pr_details = fetch_pr_details(target_repo, pr_number)
        
        base_sha = pr_details.get("base", {}).get("sha")
        head_sha = pr_details.get("head", {}).get("sha")
        clone_url = pr_details.get("base", {}).get("repo", {}).get("clone_url")
        
        if not base_sha or not head_sha or not clone_url:
            raise ValueError("Could not retrieve SHA or clone URL from PR details")
            
        if not re.match(r'^[0-9a-f]{40}$', base_sha):
            raise ValueError(f"Invalid base_sha: {base_sha}")
        if not re.match(r'^[0-9a-f]{40}$', head_sha):
            raise ValueError(f"Invalid head_sha: {head_sha}")
        if not clone_url.startswith(("https://", "git@")):
            raise ValueError(f"Suspicious URL: {clone_url}")
            
        # 2. Checkout base_sha and fetch PR ref
        logger.info(f"Checking out base commit: {base_sha}")
        repo_dir = checkout_repo(clone_url, target_repo, base_sha)
        
        logger.info(f"Fetching PR #{pr_number} commits...")
        subprocess.run(
            ["git", "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"],
            cwd=repo_dir, check=True, timeout=300
        )
        
        # 3. Determine changed files
        logger.info("Determining changed files...")
        changed_files = get_changed_files(repo_dir, base_sha, head_sha)
        logger.info(f"Changed files: {changed_files}")
        
        if not changed_files:
            logger.info("No code files changed in this PR — nothing to analyze.")
            safe_msg = (
                "### ◈ N3MO Pull Request Impact Analysis\n\n"
                "✅ No code files were changed in this PR — nothing to analyze."
            )
            post_github_comment(target_repo, int(pr_number), safe_msg, installation_id)
            sys.exit(0)
            
        if len(changed_files) > 1000:
            raise ValueError("Too many changed files to analyze (>1000)")
            
        if any(".." in f for f in changed_files):
            raise ValueError("Path traversal detected in changed files list")

        # 4. Subscription & plan check (BEFORE expensive LOC calculation)
        max_loc = 0  # Default (deny if unknown)
        plan_name = "SaaS None"
        
        if user_id:
            from n3mo.saas_db import get_subscription
            sub = get_subscription(user_id, "user")
            sub_status = sub.get("status", "unknown")
            plan_type = str(sub.get("plan_type") or "none")

            if sub_status in ("active", "trialing"):
                max_loc, plan_name = _get_plan_limits(plan_type, sub)
            else:
                max_loc = 0
                logger.warning(f"Subscription {sub_status} for user {user_id} (plan: {plan_type})")
                expired_msg = (
                    f"### ⚠️ N3MO Subscription Expired\n\n"
                    f"Your **{plan_type.capitalize()}** plan has expired. "
                    f"N3MO cannot run PR impact analysis without an active subscription.\n\n"
                    f"To re-enable PR checks:\n"
                    f"1. **Renew your plan** on the [N3MO dashboard](https://n3mo.shop)\n"
                    f"2. Or configure a **Self-Hosted N3MO** instance on your own infrastructure\n\n"
                    f"*If you've already renewed, it may take a few minutes to sync.*"
                )
                post_github_comment(target_repo, int(pr_number), expired_msg, installation_id)
                logger.info("Exited early — subscription not active.")
                sys.exit(0)

        # 5. LOC calculation and enforcement

        # 6. Calculate LOC and enforce limits
        # We calculate the real lines of code here. If `total_lines` exceeds the `max_loc`
        # for their specific SaaS tier, we instruct them to upgrade and abort the heavy processing.
        # We run calculate_repo_loc in a subprocess with a timeout if needed, but since it's a synchronous
        # python function we can't easily timeout unless we use multiprocessing or concurrent.futures.
        # Let's use concurrent.futures to wrap it with a timeout.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(calculate_repo_loc, repo_dir)
            try:
                total_lines = future.result(timeout=60) # 60 seconds max
            except concurrent.futures.TimeoutError:
                raise ValueError("Repository too large to analyze within time limits.")
        
        if max_loc > 0 and total_lines > max_loc:
            logger.warning(f"LOC limit exceeded for {target_repo}: {total_lines} LOC (Limit: {max_loc} for {plan_name})")
            warning_msg = (
                f"### ⚠️ N3MO Tier Limit Reached ({plan_name})\n\n"
                f"This repository contains **{total_lines:,} lines of code**, which exceeds N3MO's limit of **{max_loc:,} lines** for this plan.\n\n"
                f"To enable PR checks on this repository, please:\n"
                f"1. **Upgrade your plan** on our SaaS platform to activate a Pro or Enterprise subscription, or\n"
                f"2. Configure your own **Self-Hosted N3MO Enterprise edition** on your private infrastructure.\n\n"
                f"*Already upgraded? Make sure your payment is active in the dashboard.*"
            )
            post_github_comment(target_repo, int(pr_number), warning_msg, installation_id)
            logger.info("✅ Exited early due to LOC limit.")
            sys.exit(0)
        
        # Re-check subscription after LOC calculation to prevent race conditions during long calculations
        if user_id:
            from n3mo.saas_db import get_subscription
            sub = get_subscription(user_id, "user")
            if sub.get("status") != "active":
                logger.warning(f"Subscription became inactive during processing for user {user_id}")
                sys.exit(0)
        
        # 7. Index base commit and get impacts
        logger.info("Indexing base commit...")
        run_indexer_for_path(repo_dir)
        
        project_id = get_project_id(repo_dir)
        if not project_id:
            raise ValueError(
                f"Indexer did not create a project entry for {repo_dir}. "
                "This usually means no parseable source files were found."
            )

        base_impacts = get_impact_for_changed_files(project_id, changed_files)
        
        # 8. Checkout head_sha and index
        logger.info(f"Checking out head commit: {head_sha}")
        checkout_repo(clone_url, target_repo, head_sha)
        
        logger.info("Indexing head commit...")
        run_indexer_for_path(repo_dir)
        
        head_impacts = get_impact_for_changed_files(project_id, changed_files)
        
        # 9. Compare impacts
        logger.info("Calculating AST blast radius...")
        merged_impacts = merge_impacts(base_impacts, head_impacts)
        
        # 10. Format and post report
        markdown_report = format_impact_markdown(merged_impacts, target_repo, int(pr_number), total_lines)
        
        logger.info("Posting report to GitHub PR...")
        post_github_comment(target_repo, int(pr_number), markdown_report, installation_id)
        
        logger.info("✅ N3MO Core Engine finished successfully!")
        
    except Exception as e:
        logger.error(f"Core Engine Pipeline Failed: {e}")
        logger.error(traceback.format_exc())
        
        # Post error to PR so the user knows it failed
        error_id = str(uuid.uuid4())[:8]
        try:
            error_md = f"### ⚠️ N3MO Core Engine Failed\n\nAn internal error occurred during AST analysis (Error ID: `{error_id}`). Please contact support."
            post_github_comment(target_repo, int(pr_number), error_md, installation_id)
        except Exception as post_err:
            logger.error(f"Failed to post error comment to PR: {post_err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
