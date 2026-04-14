# Terrapyne

A Python CLI and SDK for Terraform Cloud.

We built Terrapyne because Terraform Cloud is great, but sometimes you just want to check a workspace status from your terminal or write a quick script to automate a tedious task—without fighting raw REST APIs. Terrapyne gives you a clean CLI for daily ad-hoc work and a Pydantic-typed SDK for building heavier automation.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## Installation

```bash
# If you use uv (recommended)
uv add terrapyne

# Or plain pip
pip install terrapyne
```

## CLI Workflows

When you install the package, you get the `tfc` command-line tool. We designed this tool around the actual workflows DevOps engineers do every day. Instead of just wrapping the API one-to-one, `tfc` combines calls to give you the answers you actually need.

### 1. Incident Response & Debugging
When a deploy fails, you don't want to click through 5 pages of the TFC web UI to find the error. You want the logs right now.

```bash
# Find runs that recently errored across the whole organization
tfc run errors

# Follow a run's logs in real-time as it executes
tfc run follow run-123abc456

# Pull a specific state output (like a database password) directly
tfc state outputs db_password -w my-app-prod --raw
```

### 2. Workspace Health & Cost Visibility
It can be surprisingly hard to answer simple questions like "is this workspace healthy?" or "how much does this project cost?". We built commands to surface this immediately.

```bash
# Get a health snapshot of a workspace (latest run, lock state, VCS config)
tfc workspace health my-app-prod

# See the total monthly cost estimate for an entire project
tfc project costs "Core Infrastructure"

# List out the recent run history
tfc run list -w my-app-prod --limit 5
```

### 3. Managing Variables & Configuration
Setting up a new environment often involves copying dozens of variables. Doing this manually is a nightmare.

```bash
# Copy all variables from staging to production
tfc workspace var-copy --from my-app-staging --to my-app-prod

# Clone an entire workspace, including its VCS config and variables
tfc workspace clone my-app-staging --new-name my-app-prod

# Dump all project details as JSON for a CI script
tfc project show "Core Infrastructure" --format json | jq .
```

### 4. Run Orchestration
Sometimes you need to override the normal workflow or trigger things manually.

```bash
# Trigger a new run, ignoring the normal auto-apply rules
tfc run trigger -w my-app-prod

# Cancel a run that got stuck in the queue
tfc run cancel run-123abc456

# Discard a speculative plan
tfc run discard run-123abc456
```

## SDK Usage

If you're writing your own tooling, the SDK handles the API boilerplate and gives you typed objects back. Every CLI command is built on top of this SDK.

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
