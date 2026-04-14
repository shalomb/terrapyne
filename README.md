# 🐢 Terrapyne

**The high-performance CLI & Python SDK for Terraform Cloud.**

Terrapyne (Terra + Py + Spine) is a robust orchestrator designed for DevOps engineers who need more than what the standard TFC web UI or CLI provides. It combines a rich, interactive terminal experience with a clean, Pydantic-powered SDK.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![TFC Supported](https://img.shields.io/badge/TFC-Supported-orange.svg)](https://app.terraform.io/)

---

## ✨ Features

- 📊 **Workspace Dashboard:** Instant "Health & Activity Snapshot" for any workspace.
- 📜 **Log Streaming:** Follow Terraform runs in real-time with beautiful `rich` terminal output.
- 🔍 **Plan Parser:** Deep-dive into Terraform plan files without leaving the CLI.
- 💰 **Cost Analysis:** Integrated cost estimates and trends for your infrastructure.
- 📦 **Pydantic Models:** A fully-typed SDK that makes building TFC automation a breeze.
- 🔌 **VCS Integration:** Manage VCS connections, webhooks, and commit metadata.
- 🛠️ **DevOps First:** JSON output for every command, making it perfectly pipeable for automation.

---

## 🚀 Quick Start

### Installation

```bash
# Using uv (recommended)
uv add terrapyne

# Using pip
pip install terrapyne
```

### CLI Usage

Terrapyne installs the `tfc` (and `terrapyne`) command-line tool.

```bash
# 1. View workspace health at a glance
tfc workspace show my-app-prod

# 2. List recent runs with status and duration
tfc run list -w my-app-prod --limit 5

# 3. Stream logs for a specific run
tfc run show run-123abc456 --stream

# 4. Get machine-readable output for your scripts
tfc project list --format json | jq '.[].name'
```

### SDK Usage

Building your own TFC automation? The SDK is built for speed and type safety.

```python
from terrapyne import TFCClient

with TFCClient(organization="my-org") as client:
    # Get workspace health
    ws = client.workspaces.get("web-frontend")
    print(f"Status: {ws.status}")

    # List active runs
    runs, total = client.runs.list(workspace_id=ws.id, status="applied")
    for run in runs:
        print(f"Run {run.id}: {run.message}")
```

---

## 📚 Documentation

For deep-dives into the architecture, design decisions (ADRs), and user guides:

- [Architecture Decision Records (ADRs)](docs/architecture/) — Why we built it this way.
- [SDK Guide](docs/SDK.md) — Exhaustive SDK reference.
- [BDD Specifications](docs/guides/bdd-specifications.md) — Living documentation of features.
- [Plan Parser Analysis](docs/terraform-plan-parser-analysis.md) — Deep-dive into plan parsing.

---

## 🏗️ Engineering Standards

Terrapyne is built with extreme engineering rigor. We follow:

- **Farley TDD:** Every feature is built using strict Red-Green-Refactor cycles.
- **Adzic BDD:** User behaviors are defined in Gherkin `.feature` files to ensure they meet real-world needs.
- **Atomic Commits:** Every change is self-contained, tested, and documented.

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).
