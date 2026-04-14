# Terrapyne

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/your-org/terrapyne/actions/workflows/pytest.yaml/badge.svg)](https://github.com/your-org/terrapyne/actions/workflows/pytest.yaml)
[![codecov](https://codecov.io/gh/your-org/terrapyne/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/terrapyne)

**A Python CLI and strongly-typed SDK for Terraform Cloud.**

Terraform Cloud (TFC) is a powerful platform, but building higher-order automation on top of its raw REST API is tedious. You find yourself writing the same pagination logic, state-polling loops, and JSON parsing over and over.

**Terrapyne** bridges this gap. It provides a robust, Pydantic-typed Python SDK for complex automation (CI/CD pipelines, internal developer portals, AI agents) and a clean, Unix-friendly CLI for your daily ad-hoc workflows.

---

## ⚡ Why Terrapyne? (The 30-Second Skim)

For the DevOps and Platform Engineer, Terrapyne is built to get out of your way:

- **Unix-Philosophy CLI**: Stop clicking through the UI. Every command supports `--format json`, so you can pipe TFC state directly into `jq`, `grep`, or your CI/CD scripts.
- **Type-Safe SDK**: Full Pydantic models for TFC resources. Catch errors in your IDE, not at runtime.
- **Higher-Order Abstractions**: Stop writing `while True:` loops to poll run status. Terrapyne handles polling, pagination, and log streaming natively.
- **Built for AI & Agents**: Structured outputs and clean interfaces make Terrapyne the perfect toolchain for LLMs and autonomous agents managing infrastructure.

---

## 🛠️ The CLI: CI/CD & Terminal Workflows

The `tfc` CLI isn't just a 1:1 API wrapper; it's designed around the questions infrastructure engineers actually ask when they get paged.

### Diagnostics & Incident Response
Get answers fast, right where your tools are.

```bash
# Find failing runs across all your workspaces instantly
tfc run errors

# Get raw state outputs to use in local scripts or debugging
tfc state outputs db_connection_string -w db-production --raw

# Tail live logs for a stuck plan right in your terminal
tfc run follow run-123abc456
```

### Scripting & Pipelines
JSON output is a first-class citizen, making pipeline integration trivial.

```bash
# Get all workspaces in a project and feed them into a script
tfc project show "Core Infrastructure" --format json | jq -r '.workspaces[].name'

# Clone a staging environment and trigger a run programmatically
tfc workspace clone app-staging --new-name app-pentest
tfc run trigger -w app-pentest --format json
```

---

## 🏗️ The SDK: Higher-Order Automation

If you are building custom tooling, GitOps bots, or internal portals, the Terrapyne SDK provides the heavy lifting.

```python
from terrapyne import TFCClient

with TFCClient(organization="my-org") as client:
    # 1. Type-safe resource fetching
    ws = client.workspaces.get("web-frontend")
    
    # 2. Trigger a plan with native Python objects
    run = client.runs.create(
        workspace_id=ws.id,
        message="Automated infrastructure update via Terrapyne",
    )
    print(f"Started run: {run.id}")

    # 3. Built-in blocking and polling (no manual loops required)
    final_run = client.runs.poll_until_complete(
        run.id,
        callback=lambda r: print(f"Status: {r.status.value}")
    )

    if final_run.status.value == "planned":
        print("Plan finished. Ready for automated or manual review.")
```

### Advanced Automation

Terrapyne makes it easy to orchestrate complex workflows, like discovering a workspace's VCS repository and triggering a plan with real-time status polling.

```python
from terrapyne import TFCClient

with TFCClient(organization="my-org") as client:
    # 1. Discover VCS details for a workspace
    vcs = client.vcs.get_workspace_vcs(workspace_id="ws-123")
    if vcs:
        print(f"Connected to: {vcs.identifier} ({vcs.branch})")

    # 2. Trigger a new plan with a custom message
    run = client.runs.create(
        workspace_id="ws-123",
        message="SDK-triggered infrastructure update",
        debug=True  # Enables TFC debugging-mode
    )
    print(f"Run triggered: {run.id}")

    # 3. Poll until the plan is ready or fails
    final_run = client.runs.poll_until_complete(
        run.id,
        callback=lambda r: print(f"Current Status: {r.status.value}")
    )

    if final_run.status.value == "planned":
        print("✅ Plan complete! Review the changes in TFC.")
```

---

## 📦 Installation

```bash
# Recommended (using uv)
uv add terrapyne

# Or via standard pip
pip install terrapyne
```

## 📚 Documentation

Dive deeper into Terrapyne's capabilities and design:

- [SDK Guide](docs/reference/sdk.md) — Reference for the Python library.
- [Architecture Decision Records (ADRs)](docs/explanation/architecture/) — Why we made certain design choices.
- [BDD Specifications](docs/explanation/bdd-specifications.md) — The behavior specifications driving the features.
- [Plan Parser Analysis](docs/explanation/plan-parser.md) — Details on how we extract data from plain text plans.

## 🧪 Engineering Standards

We hold Terrapyne to strict quality standards:
- **TDD / Red-Green-Refactor**: Driven by the Farley TDD principles.
- **BDD**: Adzic-style Gherkin feature files (`tests/features/`) for real-world behaviors.
- **Atomic Commits**: Strict Conventional Commits protocol.

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).
