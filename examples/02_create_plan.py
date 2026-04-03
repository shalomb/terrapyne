#!/usr/bin/env python3
"""Example: Create a new run (plan) and poll it.

Usage:
    export TF_CLOUD_TOKEN=your-token
    python examples/02_create_plan.py <organization> <workspace-id>
"""

import sys

from terrapyne import RunsAPI, TFCClient


def main():
    if len(sys.argv) < 3:
        print("Usage: python 02_create_plan.py <organization> <workspace-id>")
        sys.exit(1)

    org = sys.argv[1]
    workspace_id = sys.argv[2]

    # Initialize client
    client = TFCClient(organization=org)
    runs_api = RunsAPI(client)

    # 1. Create a new run (this will trigger a plan in TFC)
    print(f"Triggering plan for workspace {workspace_id}...")
    run = runs_api.create(
        workspace_id=workspace_id, message="Created via Terrapyne SDK", auto_apply=False
    )
    print(f"Created run: {run.id} (Status: {run.status})")

    # 2. Poll the run status until it reaches a terminal state (succeeded, errored, etc.)
    # We pass a callback to print the status on each poll.
    def poll_callback(current_run):
        print(f"  Current status: {current_run.status}")

    print("Polling status...")
    final_run = runs_api.poll_until_complete(run.id, callback=poll_callback)

    print(f"\nFinal status for run {final_run.id}: {final_run.status}")
    print(f"URL: {final_run.html_url}")


if __name__ == "__main__":
    main()
