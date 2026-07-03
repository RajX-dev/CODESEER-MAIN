# N3MO Agent Rules

## Dual-Repo Sync Rules
- **CRITICAL**: Never sync the `public/` directory (the website frontend) to the public `main` branch. It belongs strictly to the SaaS repository.
- **CRITICAL**: Never sync files containing SaaS logic (e.g. `saas_webhook_handler.py`, Stripe integration, billing) to the public `main` branch.
- Only documentation (like `README.md`) and core engine files can be synced to the public repository.
- Always use `scrub_readme.py` or manually verify the absence of proprietary SaaS features before pushing documentation to the public repository.
