# ADR-002: Run Model Enrichment via Included Resources

**Date:** 2026-04-12  
**Status:** Proposed  
**Relates to:** feat/workspace-dashboard, workspace-enrichment feature branch  

## Context

The Run model represents a Terraform Cloud run in the terrapyne library. TFC API responses include related resources in an `included` array (configuration-version, plan, apply, etc.). 

Currently, Run only captures direct attributes from the run's `attributes` and `relationships` sections. To support workspace-dashboard, we need to extract metadata from included `configuration-version` resources (commit SHA, author, message).

This ADR documents the pattern for safely enriching the Run model with data from included resources.

## Decision

**Run model enrichment happens at construction time via from_api_response()**

```python
class Run(BaseModel):
    # Direct attributes from run.attributes
    id: str
    status: RunStatus
    created_at: datetime | None = None
    
    # Enriched from included configuration-version
    commit_sha: str | None = None
    commit_message: str | None = None
    commit_author: str | None = None

    @classmethod
    def from_api_response(
        cls, 
        data: dict[str, Any], 
        included: list[dict[str, Any]] | None = None
    ) -> "Run":
        # ... extract direct attributes ...
        
        # Extract from included resources
        if included:
            for item in included:
                if item.get("type") == "configuration-versions":
                    cv_attrs = item.get("attributes", {})
                    ingress = cv_attrs.get("ingress-attributes", {})
                    commit_sha = ingress.get("commit-sha")
                    commit_message = ingress.get("commit-message")
                    commit_author = ingress.get("commit-author")
```

**Rationale:**
1. **Single point of hydration:** All model construction goes through `from_api_response()`, making it the clear place to handle includes
2. **Type safety:** Pydantic validation happens in one place; enriched fields are fully typed
3. **Null safety:** Enriched fields default to None; no "undefined" state
4. **Composability:** Easy to add new enrichments (e.g., resource counts from plan) without changing the API
5. **Testability:** Mock `included` parameter in tests; no need to fiddle with API responses

## Pattern Details

### What gets enriched

| Field | Source | Optional | Use Case |
|-------|--------|----------|----------|
| `commit_sha` | `included[].attributes.ingress-attributes.commit-sha` | Yes | Identify VCS commit for run's config |
| `commit_message` | `included[].attributes.ingress-attributes.commit-message` | Yes | Display commit context in UI |
| `commit_author` | `included[].attributes.ingress-attributes.commit-author` | Yes | Track who pushed the change |
| `additions` | `included[].attributes.resource-additions` (from plan) | Yes | Display resource change counts |
| `changes` | `included[].attributes.resource-changes` (from plan) | Yes | " |
| `destructions` | `included[].attributes.resource-destructions` (from plan) | Yes | " |

### Resilience

- If `included` is None/empty: enriched fields remain None (expected)
- If relationship ID doesn't match any included resource: field remains None (safe)
- If `ingress-attributes` is missing: field remains None (VCS may not be configured)
- No exceptions raised for missing includes (graceful degradation)

### Usage in API calls

API methods pass `included` parameter through:

```python
# In RunsAPI.list()
runs = []
for item in data:
    runs.append(Run.from_api_response(item, included=included))

# In RunsAPI.get()
return Run.from_api_response(response["data"], included=response.get("included"))
```

The API layer controls what's included; the Run model just uses what's provided.

## Alternatives Considered

### A1: Lazy-load enriched fields
```python
@property
def commit_sha(self) -> str | None:
    # Fetch from API if not cached
```
- **Rejected:** Adds implicit I/O to property access; unpredictable performance
- Breaks separation of concerns (Run shouldn't know about API)

### A2: Separate enrichment step after construction
```python
run = Run.from_api_response(data)
run = enrich_from_includes(run, included)
```
- **Rejected:** Two-step construction is error-prone (easy to miss enrichment)
- Less clean than single construction method

### A3: Store raw included dict on Run
```python
class Run(BaseModel):
    _raw_included: dict  # For future enrichments
```
- **Rejected:** Leaky abstraction; couples model to API format
- Better to update `from_api_response()` when new enrichments needed

### A4: Enrich at the API call site
```python
run = client.runs.get(run_id, include="configuration-version")
run.commit_sha = run.extract_commit_from_included()
```
- **Rejected:** Scatters enrichment logic; violates DRY
- API layer would need to know about every enrichment

## Consequences

**Benefits:**
- Clear, single point where hydration happens
- Supports multiple enrichments without API bloat
- Type-safe and testable
- Graceful when includes unavailable
- Minimal API surface changes (just optional param)

**Trade-offs:**
- If new enrichments needed, must update both model fields and `from_api_response()`
  - Not a problem; clear pattern to follow
- Depends on API providing includes; if removed, graceful fallback to None
  - Acceptable; feature degrades cleanly

**Future extensibility:**
- To add resource counts: add `additions`, `changes`, `destructions` fields and extraction logic in `from_api_response()`
- To add apply details: extract from `applies` included resources
- Pattern scales to any related resource in TFC API

## Related ADRs
- ADR-001: Workspace Dashboard Architecture
- ADR-003: API Include Parameter Design

## References
- Run model: src/terrapyne/models/run.py
- RunsAPI: src/terrapyne/api/runs.py
- TFC API docs: https://developer.hashicorp.com/terraform/cloud-docs/api-docs/run
