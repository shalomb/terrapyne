# Quickstart Guide

Get up and running with Terrapyne in under 5 minutes.

## 1. Installation

Terrapyne requires Python 3.12 or later. We recommend using `uv` for the fastest installation.

```bash
# Recommended (using uv)
uv add terrapyne

# Or via standard pip
pip install terrapyne
```

## 2. Authentication

Terrapyne automatically looks for your Terraform Cloud credentials. You have two options:

### Option A: `terraform login` (Recommended)
If you already have the Terraform CLI installed, simply run:
```bash
terraform login
```
Terrapyne will automatically find and use the token stored in your `~/.terraform.d/credentials.tfrc.json`.

### Option B: Environment Variable
If you don't want to use the Terraform CLI, you can set an environment variable:
```bash
export TFC_TOKEN="your-api-token-here"
```

## 3. First CLI Command

Terrapyne works best when you are in a directory with a Terraform configuration, but you can also pass the organization explicitly.

```bash
# List all workspaces in your organization
tfc workspace list --organization your-org-name
```

## 4. First SDK Script

Create a file named `check_health.py`:

```python
from terrapyne import TFCClient

# terrapyne will use your credentials automatically
with TFCClient(organization="your-org-name") as client:
    # Get a list of workspaces
    workspaces, total = client.workspaces.list()
    
    print(f"Checking {total} workspaces...\n")
    for ws in workspaces:
        # Fetch the latest run for each workspace
        runs, _ = client.runs.list(workspace_id=ws.id, limit=1)
        latest_status = runs[0].status.value if runs else "No runs"
        print(f"[{ws.name}] Status: {latest_status}")
```

Run it:
```bash
python check_health.py
```

## 🚀 Next Steps

- **Dive into the CLI**: Explore the [CLI Command Reference](../reference/cli-reference.md).
- **Build with the SDK**: Check out the [SDK Reference](../reference/sdk.md).
- **Learn the logic**: Read about our [Design Philosophy](../explanation/design-philosophy.md).
