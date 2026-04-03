#!/usr/bin/env python3
"""Example: Clone an existing workspace.

Usage:
    export TF_CLOUD_TOKEN=your-token
    python examples/04_clone_workspace.py <organization> <source-workspace> <target-workspace>
"""

import sys

from terrapyne import CloneWorkspaceAPI, TFCClient


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: python 04_clone_workspace.py <organization> <source-workspace> <target-workspace>"
        )
        sys.exit(1)

    org = sys.argv[1]
    source_name = sys.argv[2]
    target_name = sys.argv[3]

    # Initialize client
    client = TFCClient(organization=org)
    clone_api = CloneWorkspaceAPI(client)

    # Clone workspace with variables and tags
    print(f"Cloning workspace '{source_name}' to '{target_name}'...")
    result = clone_api.clone(
        source_workspace_name=source_name,
        target_workspace_name=target_name,
        with_variables=True,
        # with_vcs=True,  # requires vcs_oauth_token_id
        force=False,
    )

    if result["status"] == "success":
        print("Successfully cloned workspace!")
        print(f"Target ID: {result['target_workspace_id']}")

        # Print summary of results
        vars_result = result["results"].get("variables")
        if vars_result:
            print(f"Variables cloned: {vars_result['variables_cloned']}")
    else:
        print(f"Clone failed: {result.get('error')}")


if __name__ == "__main__":
    main()
