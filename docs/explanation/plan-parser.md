# Plan Parser

## What it is

The plan parser extracts structured data from Terraform plain-text plan output. It returns a dictionary describing resource changes, a plan summary (add/change/destroy counts), and any diagnostic errors.

## Why it exists

Terraform Cloud's remote backend does not support `terraform plan -json` or `terraform plan -out=`. The only machine-readable option is capturing the plain-text output of `terraform plan` and parsing it. The plan parser solves this by implementing a state-machine that strips ANSI codes and identifies resource blocks, attributes, and plan summaries from that output.

## When to use it

Use the plan parser when:
- You are running Terraform against a TFC remote backend and need structured change data before creating a run.
- You want to count or classify resource changes (creates, destroys, imports) from a captured plan log.
- You are building a pre-apply validation step that does not have access to a JSON plan file.

Do not use it for local Terraform workflows where `terraform plan -json` is available — use the JSON output instead.

## Usage

```python
from terrapyne import PlanParser

parser = PlanParser()
result = parser.parse(plan_text)

print(f"Status: {result['status']}")
for resource in result.get("resources", []):
    print(f"  {resource['address']}: {resource['change']['actions']}")
```

`result` contains:
- `status` — overall plan status (`planned`, `no_changes`, `errored`)
- `resources` — list of resource change objects with `address`, `type`, `name`, and `change`
- `plan_summary` — `{"add": N, "change": N, "destroy": N, "import": N}`
- `diagnostics` — list of Terraform error/warning messages
