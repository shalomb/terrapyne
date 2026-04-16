# How to List Workspaces by Project

When managing a large Terraform Cloud organization, you often need to filter workspaces by their associated project.

## Using the CLI

You can use the `tfc project show` command to see all workspaces within a specific project.

```bash
# Show details and workspaces for a project
tfc project show "Core Infrastructure"
```

### Filtering with `jq`
For more advanced filtering, use the `--format json` flag and `jq`.

```bash
# Get only the names of workspaces in a project
tfc project show "Core Infrastructure" --format json | jq -r '.workspaces[].name'

# Count workspaces in a project
tfc project show "Core Infrastructure" --format json | jq '.workspaces | length'
```

---

## Using the SDK

You can achieve this in the SDK by first getting the project and then iterating over its workspaces.

```python
from terrapyne import TFCClient

with TFCClient(organization="my-org") as client:
    # Find the project by name
    projects, _ = client.projects.list()
    target_project = next(p for p in projects if p.name == "Core Infrastructure")
    
    # List workspaces and filter by project_id
    # Note: TFC allows filtering workspaces by project ID in the list API
    workspaces, total = client.workspaces.list(project_id=target_project.id)
    
    print(f"Project: {target_project.name}")
    for ws in workspaces:
        print(f" - {ws.name}")
```
