# N3MO Privacy Policy

N3MO ("we", "our", or "us") is dedicated to protecting the privacy of developers and organizations using our code intelligence tools.

## 1. Code Privacy and Data Practices
* **Local Ingestion:** When using the N3MO CLI or MCP server locally, all parsing, AST analysis, and database storage (PostgreSQL) occur entirely on your own local machine. We do not collect, upload, or have access to any of your source code, file structures, or indexing data.
* **GitHub Integration (SaaS/Webhook):** If you install the N3MO GitHub App or integrate our webhook handler, N3MO clones the target codebase temporarily to perform the Lines of Code (LOC) check and run the delta blast radius analysis. Source code is never retained on our servers after the pull request check completes, and it is never shared with third parties.
* **No Third-Party APIs:** N3MO does not rely on any third-party AI models or external APIs. All call graph analysis is performed locally using the Tree-sitter parser and PostgreSQL recursive queries.

## 2. Information We Collect
We only process the minimal configuration metadata required for authentication and subscription checks (such as GitHub account IDs, public organization names, and subscription status) for users subscribed to the SaaS/Marketplace service.

## 3. Contact Us
For any questions or privacy inquiries, please open an issue on our official GitHub repository: [GitHub Issues](https://github.com/RajX-dev/N3MO/issues).
