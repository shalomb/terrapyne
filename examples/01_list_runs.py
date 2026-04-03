#!/usr/bin/env python3
"""Example: List recent runs in a workspace.

Usage:
    export TF_CLOUD_TOKEN=your-token
    python examples/01_list_runs.py <organization> <workspace-id>
"""

import sys

from terrapyne import RunsAPI, TFCClient


def main():
    if len(sys.argv) < 3:
        print("Usage: python 01_list_runs.py <organization> <workspace-id>")
        sys.exit(1)

    org = sys.argv[1]
    workspace_id = sys.argv[2]

    # Initialize client (uses TF_CLOUD_TOKEN environment variable by default)
    client = TFCClient(organization=org)

    # Use the RunsAPI manager
    runs_api = RunsAPI(client)

    print(f"--- Recent runs for workspace {workspace_id} ---")
    runs, total = runs_api.list(workspace_id=workspace_id, limit=5)

    if not runs:
        print("No runs found.")
        return

    for run in runs:
        print(f"Run {run.id}:")
        print(f"  Status:  {run.status}")
        print(f"  Message: {run.message}")
        print(f"  Created: {run.created_at}")
        print(f"  URL:     {run.html_url}")
        print()

    if total:
        print(f"Showing 5 of {total} total runs.")


if __name__ == "__main__":
    main()
