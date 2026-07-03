# N3MO Agent Rules

## General Workflow Rules
- **Testing**: Always perform local testing (e.g., run `mypy`, `pytest`, `ruff`) to ensure everything works before making any commits.
- **Naming Conventions**: Ensure variable, function, and file naming conventions are consistently good, clear, and descriptive.
- **Documentation**: Always review the `README.md` and related documentation to determine if it needs updating alongside code changes.

## Dual-Repo Sync Rules
- **CRITICAL PRE-CHECK**: Before pushing any changes, explicitly determine exactly which files need to be committed and where they belong (SaaS repo vs Public repo).
- **CRITICAL**: Never sync the `public/` directory (the website frontend) to the public `main` branch. It belongs strictly to the SaaS repository.
- **CRITICAL**: Never sync files containing SaaS logic (e.g. `saas_webhook_handler.py`, Stripe integration, billing) to the public `main` branch.
- Only documentation (like `README.md`) and core engine files can be synced to the public repository.
- Always use `scrub_readme.py` or manually verify the absence of proprietary SaaS features before pushing documentation to the public repository.
