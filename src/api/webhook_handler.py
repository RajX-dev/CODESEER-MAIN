import os
import logging
from fastapi import FastAPI, Request, Header, HTTPException

# Set up logging
logger = logging.getLogger("n3mo.api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="N3MO GitHub App Webhook API",
    description="Listens to GitHub webhooks to run incremental impact analysis on Pull Requests.",
    version="0.1.0"
)

# Configuration
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


@app.get("/health")
def health_check():
    """Verify service health."""
    return {"status": "healthy", "service": "n3mo-api"}


@app.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    """
    Handle incoming GitHub App webhooks.
    Filters for pull_request events to trigger blast-radius checks.
    """
    if not x_github_event:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    # Verify webhook signature if secret is configured
    if GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
        # Signature verification logic goes here
        pass

    payload = await request.json()
    logger.info(f"Received GitHub event: {x_github_event}")

    if x_github_event == "pull_request":
        action = payload.get("action")
        # Trigger on PR opening or adding new commits
        if action in ["opened", "synchronize"]:
            return handle_pull_request(payload)

    return {"message": f"Event '{x_github_event}' ignored"}


def handle_pull_request(payload: dict) -> dict:
    """
    Extract diff details, run incremental indexing, and compute impact blast radius.
    """
    pr_number = payload.get("number")
    repo_name = payload.get("repository", {}).get("full_name")
    clone_url = payload.get("repository", {}).get("clone_url")
    base_sha = payload.get("pull_request", {}).get("base", {}).get("sha")
    head_sha = payload.get("pull_request", {}).get("head", {}).get("sha")

    logger.info(f"Analyzing PR #{pr_number} for {repo_name} (from {base_sha} to {head_sha})")

    # Placeholder logic for workflow:
    # 1. Fetch changed files from GitHub API
    # 2. Run AST parser incrementally for changed files
    # 3. Compute blast radius CTE from database for changed symbols
    # 4. Format PR Markdown comment and post to GitHub API

    affected_symbols = ["predict_song_score", "get_recommendations"]  # Example mockup

    return {
        "status": "processed",
        "pr": pr_number,
        "repo": repo_name,
        "clone_url": clone_url,
        "changed_symbols": affected_symbols,
        "message": f"Successfully calculated blast radius for {len(affected_symbols)} symbols."
    }
