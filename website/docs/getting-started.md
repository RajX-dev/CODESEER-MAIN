---
sidebar_position: 2
title: Getting Started
---

# Installation & Quick Start

### Prerequisites

* **Docker** (Required for the PostgreSQL backend)
* **Python 3.10+**
* **Git**

### Installation

Install N3MO directly from PyPI:

```bash
# Install the package
pip install n3mo

# Start Docker containers & initialize the database
n3mo setup
```

Alternatively, for contributors running in editable mode:
```bash
git clone https://github.com/RajX-dev/N3MO.git
cd N3MO
pip install -e .
n3mo setup
```

### Next Steps
Now that N3MO is installed, you can index your first repository and start running impact analyses. See the [Usage Guide](./usage-guide) for CLI commands.
