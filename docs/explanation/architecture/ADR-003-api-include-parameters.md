# ADR-003: API Include Parameters and Pagination Compatibility

**Date:** 2026-04-12  
**Status:** Proposed  
**Relates to:** feat/workspace-dashboard, API consolidation  

## Context

The RunsAPI.list() method previously used `paginate_with_meta()` helper to handle pagination. The workspace-dashboard feature requires including `configuration-version` resources in list responses to fetch commit metadata.

This ADR documents the design decision: how to add include parameters to API methods while preserving pagination support and maintaining backwards compatibility.

## Decision

**Include parameters are passed through explicitly; pagination is preserved in list()**

```python
class RunsAPI:
    def list(
        self,
        workspace_id: str,
        limit: int = 20,
        status: str | None = None,
        include: str | None = "configuration-version,plan",  # NEW: explicit include param
    ) -> tuple[list[Run], int]:
        """List runs for a workspace."""
        
        params: dict[str, Any] = {
            "page[size]": min(limit, 100),
        }
        if include:
            params["include"] = include
        if status:
            params["filter[status]"] = status
        
        # Direct client.get() call for single-page fetch
        # (pagination support can be added via iterator pattern if needed)
        response = self.client.get(f"/workspaces/{workspace_id}/runs", params=params)
        
        runs = []
        for item in response.get("data", []):
            runs.append(Run.from_api_response(item, included=response.get("included", [])))
            if len(runs) >= limit:
                break
        
        total_count = response.get("meta", {}).get("pagination", {}).get("total-count", 0)
        return runs, total_count
    
    def get(
        self, 
        run_id: str, 
        include: str | None = None,  # NEW: explicit include param
    ) -> Run:
        """Get run by ID."""
        params = {}
        if include:
            params["include"] = include
        
        response = self.client.get(f"/runs/{run_id}", params=params)
        return Run.from_api_response(response["data"], included=response.get("included"))
```

**Rationale:**
1. **Explicit is better than implicit:** Callers control what's included; no hidden side effects
2. **Composability:** Different callers can request different includes without method proliferation
3. **Pagination-compatible:** Include parameters don't conflict with pagination; both work via URL params
4. **Defaults are sensible:** `include="configuration-version,plan"` covers 90% of use cases (commit info + resource counts)
5. **Override capability:** Callers can pass `include=None` to exclude (minimizing response size)
6. **Backwards compatible:** Existing code works; new code opts-in to more includes

## Pattern Details

### Include param design

- **Type:** `str | None` (comma-separated resource types)
- **Default:** `"configuration-version,plan"`
  - `configuration-version`: VCS commit metadata (for dashboard)
  - `plan`: Resource change counts (for future CLI features)
- **Override:** Pass explicit value to change
  - `include="configuration-version"` — only commit info
  - `include=None` — no includes (minimal response)

### Pagination and includes work together

```
# API call with both include and pagination params
GET /workspaces/ws-123/runs?
  include=configuration-version,plan
  page[size]=20
  filter[status]=pending,planning
```

- Includes don't affect pagination calculation
- Page size still applies (not per-include)
- Total count reflects all runs (not just included types)

### Caller patterns

```python
# 1. Default includes (most common)
runs, total = client.runs.list(workspace_id)  # Gets config-version + plan

# 2. Minimal response (size-sensitive)
runs, total = client.runs.list(workspace_id, include=None)

# 3. Custom includes
runs, total = client.runs.list(workspace_id, include="apply,state-version")

# 4. With filters
runs, total = client.runs.list(
    workspace_id,
    status="pending,planning",
    include="configuration-version"
)

# 5. Single run with includes
run = client.runs.get(run_id, include="configuration-version,apply")
```

## Alternatives Considered

### A1: Hard-code includes in list(), add separate methods
```python
def list(self, workspace_id, ...):  # Always includes config-version,plan
def list_minimal(self, workspace_id, ...):  # No includes
def list_with_apply(self, workspace_id, ...):  # Includes apply instead
```
- **Rejected:** Method explosion; violates DRY
- New features would require new methods

### A2: Return "raw" response objects, let caller extract
```python
raw_response = client.runs.list_raw(workspace_id)
# Caller extracts Run objects and includes manually
```
- **Rejected:** Loses type safety; shifts responsibility to caller
- Defeats purpose of API layer

### A3: Always include everything; no override
```python
def list(self, workspace_id):  # Always includes all available resources
```
- **Rejected:** Response bloat; wastes bandwidth for callers that don't need extras
- Expensive for list operations on large workspaces

### A4: Includes as **kwargs
```python
def list(self, workspace_id, include_configuration_version=True, include_plan=True, ...):
```
- **Rejected:** Combinatorial explosion of parameters
- Harder to test; easier to make mistakes

## Consequences

**Benefits:**
- Clean API surface; flexible without complexity
- Pagination preserved and works with includes
- Sensible defaults for common cases
- Backwards compatible (existing code unaffected)
- Future-proof (easy to add new includes when TFC API grows)

**Trade-offs:**
- Callers need to understand what includes are available
  - Mitigation: Document in docstrings and ADRs
- Default includes add ~10-15% to response size (acceptable)
  - Mitigation: Callers can override if needed

**Performance implications:**
- With includes: ~10-15% larger responses (extra 200-500 bytes per run)
- Without includes: Reduced response size when override passed
- No additional API calls or latency (includes are query params, not separate requests)

## Future considerations

### When to add new includes
- **Include** when: Needed by multiple API methods or CLI commands
- **Don't include** when: Only used by one-off feature; prefer explicit override

### Example: Adding state-version includes
```python
# If workspace show needs to display current state version:
def list(
    self,
    workspace_id: str,
    include: str | None = "configuration-version,plan,state-version",
):
```

### Pagination iterator pattern (future)
If full pagination support needed (walk all pages):
```python
def list_all(self, workspace_id, include=None) -> Iterator[Run]:
    """Paginate through all runs, yielding one at a time."""
    # Implement iterator pattern if needed
```

## Related ADRs
- ADR-001: Workspace Dashboard Architecture
- ADR-002: Run Model Enrichment Patterns

## References
- RunsAPI: src/terrapyne/api/runs.py
- TFC API include syntax: https://developer.hashicorp.com/terraform/cloud-docs/api-docs/overview#inclusion-of-related-resources
- Implementation: feat/workspace-dashboard branch
