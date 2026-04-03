#!/usr/bin/env python3
"""Example: List and manage workspace variables.

Usage:
    export TF_CLOUD_TOKEN=your-token
    python examples/03_batch_workspace_vars.py <organization> <workspace-name>
"""

import sys

from terrapyne import TFCClient, WorkspacesAPI


def main():
    if len(sys.argv) < 3:
        print("Usage: python 03_batch_workspace_vars.py <organization> <workspace-name>")
        sys.exit(1)

    org = sys.argv[1]
    workspace_name = sys.argv[2]

    # Initialize client
    client = TFCClient(organization=org)
    workspaces_api = WorkspacesAPI(client)

    # 1. Get workspace ID
    print(f"Fetching workspace {workspace_name}...")
    workspace = workspaces_api.get(workspace_name)
    print(f"Workspace ID: {workspace.id}")

    # 2. List variables
    print(f"\n--- Current variables for {workspace_name} ---")
    variables = workspaces_api.get_variables(workspace.id)

    if not variables:
        print("No variables found.")
    else:
        for var in variables:
            print(
                f"[{var.category.upper()}] {var.key} = {var.value if not var.sensitive else '[SENSITIVE]'}"
            )

    # 3. Create a new variable (commented out to prevent accidental changes)
    # print(f"\nCreating a new variable...")
    # new_var = workspaces_api.create_variable(
    #     workspace_id=workspace.id,
    #     key="TERRAPYNE_DEMO",
    #     value="hello-world",
    #     category="terraform"
    # )
    # print(f"Created variable {new_var.key} with ID {new_var.id}")


if __name__ == "__main__":
    main()
