# Terrapyne SDK Examples

This directory contains example scripts demonstrating how to use Terrapyne as a Python library/SDK.

## Setup

Ensure you have your Terraform Cloud token set in your environment:

```bash
export TF_CLOUD_TOKEN=your-token-here
```

## Running Examples

You can run these examples using `uv`:

```bash
uv run examples/01_list_runs.py
```

## List of Examples

- `01_list_runs.py`: List the most recent runs in a workspace.
- `02_create_plan.py`: Create a new run (plan) and poll it until completion.
- `03_batch_workspace_vars.py`: List and update variables in a workspace.
- `04_clone_workspace.py`: Clone an existing workspace.
