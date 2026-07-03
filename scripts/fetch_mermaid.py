import base64
import json
import urllib.request
import os

def download_mermaid(mermaid_code, output_filename):
    # Create the JSON payload expected by mermaid.ink
    payload = json.dumps({
        "code": mermaid_code,
        "mermaid": {"theme": "default"}
    }).encode('utf-8')
    
    # Base64 encode the payload (URL safe)
    encoded = base64.b64encode(payload).decode('utf-8')
    url = f"https://mermaid.ink/img/{encoded}"
    
    try:
        print(f"Downloading {output_filename}...")
        urllib.request.urlretrieve(url, output_filename)
        print(f"Successfully saved {output_filename}")
    except Exception as e:
        print(f"Failed to download {output_filename}: {e}")

er_diagram = """erDiagram
    PROJECT ||--o{ SYMBOL : contains
    PROJECT ||--o{ CALL : tracks
    PROJECT ||--o{ IMPORT : tracks
    PROJECT ||--o{ FILE : indexes
    SYMBOL ||--o{ CALL : "source of"
    SYMBOL ||--o{ CALL : "resolved to"
    SYMBOL ||--o{ SYMBOL : "parent of"

    PROJECT {
        uuid id PK
        text name
        text repo_url
        timestamp created_at
    }
    SYMBOL {
        uuid id PK
        uuid project_id FK
        text name
        text file_path
        text kind "function|class|method"
        uuid parent_id FK
    }
    CALL {
        uuid id PK
        uuid source_symbol_id FK
        text call_name
        uuid resolved_symbol_id FK
    }
"""

architecture = """graph TD
    A["📄 Source Code"] -->|Tree-sitter| B["🌳 AST Parser"]
    B --> C["🔍 Symbol Extractor"]
    D["🔄 Git Hooks"] -->|post-commit| A

    C --> E[("🗄️ PostgreSQL<br/>Projects · Symbols · Calls<br/>Imports · Files")]

    E --> F["💥 Impact Analysis Engine"]
    E --> G["📞 Call Graph API"]

    F --> I["🎨 vis.js Visualizer"]
    G --> I

    F --> J["🤖 MCP Server"]

    style A fill:#6c63ff,stroke:#4a3fbf,color:#fff
    style B fill:#7c74ff,stroke:#4a3fbf,color:#fff
    style C fill:#7c74ff,stroke:#4a3fbf,color:#fff
    style D fill:#ffd93d,stroke:#d4b800,color:#1a202c
    style E fill:#ff6b6b,stroke:#c53030,color:#fff,stroke-width:3px
    style F fill:#45b7d1,stroke:#2c8ea8,color:#1a202c
    style G fill:#45b7d1,stroke:#2c8ea8,color:#1a202c
    style I fill:#9ae6b4,stroke:#2f855a,color:#1a202c
    style J fill:#ffd93d,stroke:#d4b800,color:#1a202c
"""

os.makedirs('paper', exist_ok=True)
download_mermaid(er_diagram, "paper/er_diagram.png")
download_mermaid(architecture, "paper/architecture.png")
