import os
import sys
import logging
import subprocess
import urllib.request
import urllib.error
import json
import traceback

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
    
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _get_plan_limits(plan_type: str, sub: dict = None) -> tuple[int, str]:
    """Return (max_loc, plan_name) for a given plan type based on subscription data."""
    if sub and sub.get("pricing_version") == "2":
        loc_limit = sub.get("loc_per_repo_limit")
        if loc_limit == -1:
            loc_limit = 99999999
        return (loc_limit or 0, f"SaaS {plan_type.capitalize()}")
    
    plan_map = {
        "enterprise": (-1, "SaaS Enterprise"),
        "team": (1000000, "SaaS Team"),
        "pro": (100000, "SaaS Pro"),
        "starter": (30000, "SaaS Starter"),
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
        is_private = pr_details.get("base", {}).get("repo", {}).get("private", True)
        
        if not base_sha or not head_sha or not clone_url:
            raise ValueError("Could not retrieve SHA or clone URL from PR details")
            
        # 2. Checkout base_sha and fetch PR ref
        logger.info(f"Checking out base commit: {base_sha}")
        repo_dir = checkout_repo(clone_url, target_repo, base_sha)
        
        logger.info(f"Fetching PR #{pr_number} commits...")
        subprocess.run(
            ["git", "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"],
            cwd=repo_dir, check=True
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

        # 4. Subscription & plan check (BEFORE expensive LOC calculation)
        max_loc = 0  # Default
        plan_name = "SaaS None"
        
        if user_id:
            from n3mo.saas_db import get_subscription
            sub = get_subscription(user_id, "user")
            sub_status = sub.get("status", "unknown")
            plan_type = str(sub.get("plan_type") or "none")

            if sub_status == "active":
                max_loc, plan_name = _get_plan_limits(plan_type, sub)
            elif sub_status in ("expired", "cancelled", "canceled"):
                # Open-source repos are free — only block on private repos
                if is_private:
                    logger.warning(f"Subscription {sub_status} for user {user_id} (plan: {plan_type})")
                    expired_msg = (
                        f"### ⚠️ N3MO Subscription {sub_status.capitalize()}\n\n"
                        f"Your **{plan_type.capitalize()}** plan has {sub_status}. "
                        f"N3MO cannot run PR impact analysis on private repositories without an active subscription.\n\n"
                        f"To re-enable PR checks:\n"
                        f"1. **Renew your plan** on the [N3MO dashboard](https://n3mo.shop)\n"
                        f"2. Or configure a **Self-Hosted N3MO** instance on your own infrastructure\n\n"
                        f"*If you've already renewed, it may take a few minutes to sync.*"
                    )
                    post_github_comment(target_repo, int(pr_number), expired_msg, installation_id)
                    logger.info("Exited early — subscription not active on private repo.")
                    sys.exit(0)
                else:
                    logger.info(f"Subscription {sub_status} but repo is public — proceeding with open-source access.")

        # 5. Open-source override: public repos get unlimited LOC
        if not is_private:
            max_loc = -1
            plan_name = plan_name + " (Open Source)"

        # 6. Calculate LOC and enforce limits
        total_lines = calculate_repo_loc(repo_dir)
        
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
        try:
            error_md = f"### ⚠️ N3MO Core Engine Failed\n\nAn error occurred during AST analysis:\n```\n{e}\n```"
            post_github_comment(target_repo, int(pr_number), error_md, installation_id)
        except Exception as post_err:
            logger.error(f"Failed to post error comment to PR: {post_err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
