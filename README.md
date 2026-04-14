# Terrapyne

A Python CLI and SDK for Terraform Cloud.

Terraform Cloud is great, but sometimes you just want to check a workspace status from your terminal or write a quick Python script to automate a tedious task without fighting raw REST APIs. Terrapyne gives you a clean CLI for daily ad-hoc work and a Pydantic-typed SDK for building heavier automation.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## Use Cases

Depending on what you're trying to do, you can use Terrapyne in a few different ways:

**Daily CLI driver**
If you're tired of clicking through the TFC UI, the `tfc` command lets you check workspace health, list runs, and stream plan logs directly in your terminal.

**CI/CD pipelines**
Every CLI command supports `--format json`. You can pipe the output straight into `jq` to extract exactly what you need for your GitHub Actions or GitLab jobs.

**Custom automation**
When bash scripts aren't enough, the Python SDK gives you typed models and API clients to build complex workflows—like bulk-updating workspace variables, triggering runs, or parsing plan outputs programmatically.

## Installation

```bash
# If you use uv (recommended)
uv add terrapyne

# Or plain pip
pip install terrapyne
```

## CLI Usage

When you install the package, you get the `tfc` command-line tool.

```bash
# Check what's happening in a workspace
tfc workspace show my-app-prod

# See recent runs
tfc run list -w my-app-prod --limit 5

# Follow the logs for a specific run in real-time
tfc run show run-123abc456 --stream

# Grab raw data for a shell script
tfc project list --format json | jq '.[].name'
```

## SDK Usage

If you're writing your own tooling, the SDK handles the API boilerplate and gives you typed objects back.

```python
from terrapyne import TFCClient

with TFCClient(organization="my-org") as client:
    # Check workspace status
    ws = client.workspaces.get("web-frontend")
    print(f"Status: {ws.status}")

    # List recent successful runs
    runs, total = client.runs.list(workspace_id=ws.id, status="applied")
    for run in runs:
        print(f"Run {run.id}: {run.message}")
```

### Orchestrating Workflows

For more involved tasks, you can string together different API calls. Here's how you might discover where a workspace's code lives, trigger a plan, and wait for it to finish.

```python
from terrapyne import TFCClient

with TFCClient(organization="my-org") as client:
    # Discover the VCS connection
    vcs = client.vcs.get_workspace_vcs(workspace_id="ws-123")
    if vcs:
        print(f"Connected to: {vcs.identifier} ({vcs.branch})")

    # Trigger a plan with debug mode on
    run = client.runs.create(
        workspace_id="ws-123",
        message="SDK-triggered infrastructure update",
        debug=True
    )
    print(f"Started run: {run.id}")

    # Block until the plan completes or fails
    final_run = client.runs.poll_until_complete(
        run.id,
        callback=lambda r: print(f"Current Status: {r.status.value}")
    )

    if final_run.status.value == "planned":
        print("Plan finished. Ready for review.")
```

## Documentation

If you want to dig into how this is built or how to use specific features:

- [Architecture Decision Records (ADRs)](docs/explanation/architecture/) — Why we made certain design choices.
- [SDK Guide](docs/reference/sdk.md) — Reference for the Python library.
- [BDD Specifications](docs/explanation/bdd-specifications.md) — The behavior specifications driving the features.
- [Plan Parser Analysis](docs/explanation/plan-parser.md) — Details on how we extract data from plain text plans.

## Engineering Standards

We try to hold ourselves to a strict standard here. The project relies heavily on Farley TDD (Red-Green-Refactor cycles), Adzic BDD (Gherkin feature files for real-world behaviors), and Atomic Commits. 

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
