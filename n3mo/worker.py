import os
import sys
import logging
import urllib.request
import urllib.error
import json
import traceback

from n3mo.core_engine import (
    checkout_repo, 
    get_changed_files, 
    calculate_repo_loc, 
    get_project_id,
    get_impact_for_changed_files,
    merge_impacts,
    format_impact_markdown,
    post_github_comment
)
from n3mo.run_indexer import run_indexer_for_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("n3mo.worker")

def fetch_pr_details(repo_full_name: str, pr_number: str) -> dict:
    github_pat = os.getenv("GITHUB_PAT")
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

def main():
    target_repo = os.getenv("TARGET_REPO")
    pr_number = os.getenv("PR_NUMBER")
    user_id = os.getenv("USER_ID")
    
    if not target_repo or not pr_number:
        logger.error("Missing TARGET_REPO or PR_NUMBER in environment")
        sys.exit(1)
    
    logger.info("â‰¡Æ’ÃœÃ‡ N3MO CORE ENGINE WAKING UP â‰¡Æ’ÃœÃ‡")
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
            raise Exception("Could not retrieve SHA or clone URL from PR details")
            
        # 2. Checkout base_sha and index
        logger.info(f"Checking out base commit: {base_sha}")
        repo_dir = checkout_repo(clone_url, target_repo, base_sha)
        
        # We need to fetch the PR ref so that the head_sha is available locally
        logger.info(f"Fetching PR #{pr_number} commits...")
        import subprocess
        subprocess.run(["git", "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"], cwd=repo_dir, check=True)
        
        # We need changed files to know what to index/query
        logger.info("Determining changed files...")
        changed_files = get_changed_files(repo_dir, base_sha, head_sha)
        logger.info(f"Changed files: {changed_files}")
        
        total_lines = calculate_repo_loc(repo_dir)
        
        # Check SaaS limits
        max_loc = 150000
        plan_name = "SaaS Starter"
        
        if user_id:
            from n3mo.saas_db import get_subscription
            sub = get_subscription(user_id, "user")
            if sub.get("status") == "active":
                plan_type_str = str(sub.get("plan_type") or "free")
                plan_name = f"SaaS {plan_type_str.capitalize()}"
                if sub.get("plan_type") == "enterprise":
                    max_loc = -1
                elif sub.get("plan_type") == "team":
                    max_loc = 1000000
                elif sub.get("plan_type") == "pro":
                    max_loc = 100000
                    
        is_private = pr_details.get("base", {}).get("repo", {}).get("private", True)
        if not is_private:
            max_loc = -1
            plan_name = plan_name + " (Open Source)"
                    
        if max_loc > 0 and total_lines > max_loc:
            logger.warning(f"LOC limit exceeded for {target_repo}: {total_lines} LOC (Limit: {max_loc} for {plan_name})")
            warning_msg = (
                f"### Î“ÃœÃ¡âˆ©â••Ã… N3MO Tier Limit Reached ({plan_name})\n\n"
                f"This repository contains **{total_lines:,} lines of code**, which exceeds N3MO's limit of **{max_loc:,} lines** for this plan.\n\n"
                f"To enable PR checks on this repository, please:\n"
                f"1. **Upgrade your plan** on our SaaS platform to activate a Pro or Enterprise subscription, or\n"
                f"2. Configure your own **Self-Hosted N3MO Enterprise edition** on your private infrastructure.\n\n"
                f"*Already upgraded? Make sure your payment is active in the dashboard.*"
            )
            post_github_comment(target_repo, int(pr_number), warning_msg, os.getenv("INSTALLATION_ID"))
            logger.info("Î“Â£Ã  Exited early due to LOC limit.")
            sys.exit(0)
        
        logger.info("Indexing base commit...")
        run_indexer_for_path(repo_dir)
        
        project_id = get_project_id(repo_dir)
        base_impacts = get_impact_for_changed_files(project_id, changed_files)
        
        # 3. Checkout head_sha and index
        logger.info(f"Checking out head commit: {head_sha}")
        checkout_repo(clone_url, target_repo, head_sha)
        
        logger.info("Indexing head commit...")
        run_indexer_for_path(repo_dir)
        
        head_impacts = get_impact_for_changed_files(project_id, changed_files)
        
        # 4. Compare impacts
        logger.info("Calculating AST blast radius...")
        merged_impacts = merge_impacts(base_impacts, head_impacts)
        
        # 5. Format and post report
        markdown_report = format_impact_markdown(merged_impacts, target_repo, int(pr_number), total_lines)
        
        logger.info("Posting report to GitHub PR...")
        post_github_comment(target_repo, int(pr_number), markdown_report, os.getenv("INSTALLATION_ID"))
        
        logger.info("Î“Â£Ã  N3MO Core Engine finished successfully!")
        
    except Exception as e:
        logger.error(f"Core Engine Pipeline Failed: {e}")
        logger.error(traceback.format_exc())
        
        # Post error to PR so the user knows it failed
        error_md = f"### Î“ÃœÃ¡âˆ©â••Ã… N3MO Core Engine Failed\n\nAn error occurred during AST analysis:\n```\n{e}\n```"
        post_github_comment(target_repo, int(pr_number), error_md, os.getenv("INSTALLATION_ID"))
        sys.exit(1)

if __name__ == "__main__":
    main()
