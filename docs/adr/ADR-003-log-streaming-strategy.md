# ADR-003: Log Streaming Strategy

## Status
Accepted

## Context
Users monitoring Terraform runs need to see the log output as it happens. Simple status polling only shows the current state (e.g., "Planning"), hiding the actual details of what Terraform is doing.

## Decision
We decided to implement log streaming by tracking the byte offset of the plan and apply log files and fetching only the delta in each poll cycle.

## Rationale (Y-Statement)
In context of command-line interactivity,
facing the user requirement for real-time visibility,
we decided for offset-based log delta fetching
to achieve a "native" Terraform CLI experience,
accepting increased API call volume during active runs.

## Consequences
+ High interactivity (matches `terraform plan/apply` feel)
+ Immediate visibility into failures or specific resource changes
+ Unified `--watch` flag behavior across all run commands
- Potential for rate-limiting if many users stream simultaneously (mitigated by exponential backoff in client)

## Alternatives Considered
- **Status-only polling**: Rejected as insufficient for developer workflows.
- **WebSocket streaming**: Rejected as TFC does not currently expose a public WebSocket for logs.
