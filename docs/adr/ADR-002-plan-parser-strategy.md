# ADR-002: Plan Parser Strategy

## Status
Accepted

## Context
Terraform Cloud provides plan outputs in multiple formats: plain text logs (captured during streaming) and structured JSON (available via separate API call after completion). Relying solely on JSON is not viable for real-time progress, but plain text parsing is notoriously brittle.

## Decision
We decided to implement a dual-mode parser: a "plain text" engine for real-time summaries and a "JSON" engine for detailed, final reporting. We also refactored the parser to be declarative, using marker-based discovery instead of sequential line-walking.

## Rationale (Y-Statement)
In context of real-time run monitoring,
facing the choice between brittle regex parsing and high-latency JSON polling,
we decided for a marker-based declarative text parser
to achieve low-latency progress reporting,
accepting that some complex structural details are only available post-run via JSON.

## Consequences
+ Sub-second progress updates during `run trigger`
+ Support for multiple Terraform versions (parsing markers instead of fixed line numbers)
+ Testable in isolation without TFC API connectivity
- Increased complexity in maintaining two parsing paths

## Alternatives Considered
- **JSON-only**: Rejected due to high latency and lack of intermediate progress.
- **Sequential text parsing**: Rejected as too brittle across Terraform versions.
