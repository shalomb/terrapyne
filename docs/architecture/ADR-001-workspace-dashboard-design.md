# ADR-001: Workspace Dashboard Architecture

**Date:** 2026-04-12  
**Status:** Proposed  
**Relates to:** feat/workspace-dashboard  

## Context

The workspace-dashboard feature adds a "Health & Activity Snapshot" panel to the `tfc workspace show` command. This panel displays:
- Workspace health status (🟢 Healthy, 🟡 Pending, 🔴 Unhealthy)
- Count of active (non-terminal) runs
- Latest commit metadata (SHA, author, message)

This requires enriching the Run model with VCS information and designing how the CLI fetches and displays this data.

## Decision

**1. Render as a composition (dashboard wraps detail)**

The workspace dashboard renders as:
1. Base workspace detail table (existing `render_workspace_detail()`)
2. Health & Activity Snapshot table (new, appended)
3. Variables section (existing)
4. VCS configuration section (existing)

**Rationale:**
- Preserves existing detail rendering logic (DRY)
- Snapshot is visually distinct (separate table)
- Allows future dashboard panels without modifying base renderer
- CLI output reads top-to-bottom naturally (details → health → resources → config)

**2. Fetch latest run and active count in a single optimized call**

```python
# Fetch 20 recent runs to establish baseline
runs, total_count = client.runs.list(ws.id, limit=20, include="configuration-version")
latest_run = runs[0] if runs else None
active_runs_count = sum(1 for r in runs if r.status in active_list)

# If we fetched max results, do a dedicated count for accurate total
if len(runs) == 20 and total_count > 20:
    _, active_runs_count = client.runs.list(ws.id, status=status_filter, limit=1)
```

**Rationale:**
- Single API call fetches both latest run (for commit info) and activity snapshot in most cases
- Avoids N+1 problem: one list call for data + optional count call
- Includes `configuration-version` by default to pull commit metadata
- Falls back to dedicated count query only when workspace has >20 active runs (rare)
- Graceful degradation: missing run data shows "Unknown" health status, not errors

**3. Enrich Run model at construction (from_api_response)**

Run model accepts an optional `included` parameter in `from_api_response()`:

```python
Run.from_api_response(data, included=response.get("included", []))
```

This extracts commit metadata (sha, message, author) from the `configuration-version` included resource.

**Rationale:**
- Commit info naturally belongs to the Run domain model
- Extraction at construction time (not lazy) keeps model behavior predictable
- Handles relationship dereferencing in one place (single responsibility)
- If `included` is empty/missing, fields remain None (safe default)
- Supports both paginated list responses and single-run fetches

**4. Include "configuration-version" in the runs.list() include parameter**

```python
def list(self, workspace_id, include="configuration-version,plan", ...):
```

**Rationale:**
- Configuration version is the VCS integration point in the TFC API
- Pulling it in list calls is cheap (minimal additional data)
- Allows CLI features to use VCS metadata without extra API calls
- Matches TFC API patterns: includes are optimizations, not requirements
- Plan inclusion useful for resource-change counts (future feature)

## Alternatives Considered

### A1: Fetch commit info via separate API call
- **Rejected:** N+1 pattern; workspace show would require 3+ API calls
- Would slow down common CLI operations

### A2: Store commit info on Workspace model instead of Run
- **Rejected:** Breaks domain boundaries; latest commit belongs to latest run, not workspace
- Workspace attributes are static (name, locked state); run metadata is dynamic

### A3: Calculate health status on the server (backend property)
- **Rejected:** Health is presentation concern (emoji, language); doesn't belong in API
- UI teams may want different health semantics (pessimistic vs optimistic)

### A4: Lazy-load included resources (commit data pulled on access)
- **Rejected:** Adds complexity; unclear when data is available
- Eager loading at construction time is simpler and testable

## Consequences

**Benefits:**
- Dashboard pattern is composable (easy to add more panels)
- API call pattern is efficient for the common case
- Run model naturally enriched, reusable across CLI commands
- Graceful degradation when run data unavailable

**Risks:**
- If TFC API removes configuration-version includes support, dashboard loses VCS data
  - Mitigation: Feature is "nice to have"; graceful fallback to health-only display
- Large workspaces with many active runs trigger an extra API call
  - Mitigation: Rare edge case; acceptable performance trade-off

**Technical Debt:**
- None immediately; design is clean and testable

## Related ADRs
- ADR-002: Run Model Enrichment Patterns
- ADR-003: API Include Parameter Design

## Implementation Notes
- See plan: /home/unop/.claude/plans/foamy-gathering-ullman.md
- Branch: feat/workspace-dashboard
- Key files: src/terrapyne/cli/workspace_cmd.py, src/terrapyne/models/run.py, src/terrapyne/utils/rich_tables.py
