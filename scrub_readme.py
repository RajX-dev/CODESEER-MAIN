import os
import re

readme_path = "README.md"
if not os.path.exists(readme_path):
    exit(0)

with open(readme_path, "r", encoding="utf-8") as f:
    content = f.read()

# Strings to remove
# 1. Mermaid node J
content = re.sub(r'\s*F --> K\["⚓ GitHub Webhook"\]', '', content)
content = re.sub(r'\s*style K fill:#ffd93d,stroke:#d4b800,color:#1a202c', '', content)
content = re.sub(r'\s*participant API as GitHub Webhook API', '', content)

# 2. Sequence diagram block
sequence_block = r'''\s*rect rgb\(26, 27, 46\)
\s*Note over API, DB: Webhook / PR Flow
\s*API->>API: Receive GitHub webhook on PR open/update
\s*API->>API: Clone/checkout head & base commit
\s*API->>API: Check LOC limit vs Subscription tier
\s*API->>DB: Index changes \(multiprocessing AST parsing\)
\s*API->>DB: Resolve call graph impacts
\s*API-->>User: Post markdown report comment on PR
\s*end'''
content = re.sub(sequence_block, '', content)

# 3. Stack table
content = re.sub(r'\| \*\*Webhook API\*\*.+\n', '', content)

# 4. Roadmap
content = re.sub(r'\| \| GitHub Webhook API \| ✅ Complete \|\n', '', content)
content = re.sub(r'- \[x\] GitHub Webhook API — automated PR blast radius reports\n', '', content)

# 5. Text sections
content = re.sub(r'- \*\*Self-Hosted Webhook:\*\* Set up your own instance of the webhook API server to run automated PR reviews for your team\.', '', content)
content = re.sub(r'\*If a self-hosted repository check exceeds the configured limits in your licensing setup, N3MO will comment on the PR prompting the team to update or configure an enterprise license key\.\*', '', content)

# 6. Webhook setup block
webhook_setup_block = r'''### ⚙️ GitHub Webhook Setup \(Self-Hosted\)

Start the API server on your deployment instance, and configure the webhook payload URL on your GitHub App or repository settings to point to `http://<your-server-ip>:8000/github/webhook`.

Set the following environment variables on your server:

- `GITHUB_TOKEN` \(or `GITHUB_PAT`\): A GitHub personal access token with permissions to read repository contents and post comments\.
- `GITHUB_WEBHOOK_SECRET`: Secure webhook verification token matching the GitHub App secret\.
- `N3MO_LICENSE_KEY`: Set this to your cryptographically signed JWT license key \(offered to Enterprise subscribers\) to unlock unlimited LOC checks\.

\*For GitHub App installations\*: Configure `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` \(or `GITHUB_APP_PRIVATE_KEY_PATH` / `GITHUB_PRIVATE_KEY_PATH`\) along with the installation ID to automatically authenticate as an App\.'''
content = re.sub(webhook_setup_block, '', content)

with open(readme_path, "w", encoding="utf-8") as f:
    f.write(content)
