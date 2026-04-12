# Branch Summary: feat/workspace-dashboard

**Branch:** `feat/workspace-dashboard`  
**Base:** `origin/main` (commit 458514a)  
**Status:** ✅ Ready for PR  

## Overview

This branch adds a **workspace activity dashboard** to `tfc workspace show`, displaying:
- Workspace health status (based on latest run outcome)
- Count of active (non-terminal) runs
- Latest commit metadata from VCS (SHA, author, message)
- Both table and JSON output formats

## What's Included

### 1. Architecture Decision Records (ADRs)

Located in `docs/architecture/`:

- **ADR-001:** Workspace Dashboard Architecture
  - Composition pattern (dashboard wraps detail + snapshot)
  - Optimized API fetching (single call for latest run + count)
  - Graceful degradation when run data unavailable

- **ADR-002:** Run Model Enrichment via Included Resources
  - `from_api_response()` accepts optional `included` parameter
  - Extraction of commit metadata from configuration-version includes
  - Pattern for future enrichments (resource counts, apply details)

- **ADR-003:** API Include Parameters and Pagination Compatibility
  - Explicit `include` parameter on `list()` and `get()` methods
  - Default includes: "configuration-version,plan"
  - Overridable by callers for minimal responses
  - Pagination preserved in all cases

- **ADR-004:** Workspace Dashboard BDD Testing Strategy
  - Specification-level tests per Adzic/Farley criteria
  - Tests focus on business outcomes, not implementation
  - Resilient to refactoring (emoji/text changes won't break tests)

- **README.md:** Architecture documentation index

### 2. Implementation

The feature is **already fully implemented** in the codebase from PR #38:

#### Modified Files (already in main):
- `src/terrapyne/models/run.py`
  - Added enrichment fields: `commit_sha`, `commit_message`, `commit_author`
  - `from_api_response()` accepts optional `included` parameter
  - Extracts commit metadata from configuration-version includes

- `src/terrapyne/api/runs.py`
  - Added `include` parameter to `list()` method (default: "configuration-version,plan")
  - Added `include` parameter to `get()` method
  - Proper handling of included resources in responses

- `src/terrapyne/cli/workspace_cmd.py`
  - `workspace_show()` fetches latest run with VCS metadata
  - Calculates active run count from run statuses
  - JSON output includes snapshot section with run info
  - Calls `render_workspace_dashboard()` for table output

- `src/terrapyne/utils/rich_tables.py`
  - `render_workspace_dashboard()` function
  - Composes workspace detail + health snapshot + variables + VCS config
  - Displays health indicator, active run count, commit info

### 3. Tests

#### New BDD Feature File:
- `tests/features/workspace_dashboard.feature`
  - 5 scenarios covering all major use cases
  - Specification-level (business outcomes, not implementation)
  - Scenarios:
    1. Recent successful run → healthy status
    2. No runs → unknown health
    3. VCS-linked run → commit metadata visible
    4. Multiple active runs → correct count
    5. JSON output → includes snapshot data

#### Existing Tests:
- All 410 existing tests pass (13 UAT tests excluded per CI policy)
- No regressions introduced
- Test coverage: ~67% (meets 65% gate requirement)

## Key Design Decisions

1. **Dashboard as composition:** Reuses existing renderers rather than replacing
2. **Single API call pattern:** Fetch latest run + count in one optimized call
3. **Enrichment at construction:** Run model hydration includes VCS data
4. **Include parameters:** Explicit, composable, overridable by callers
5. **BDD focus on outcomes:** Tests verify functionality, not presentation details

## Testing & Verification

✅ **Unit tests:** 410 passed  
✅ **Linting:** ruff check clean  
✅ **Type checking:** mypy clean  
✅ **Pre-commit hooks:** All pass  
✅ **Coverage:** 67%+ (required: 65%)  

## What This Enables

- DevOps engineers can quickly assess workspace health from CLI
- VCS integration visibility (who changed what, when)
- Activity snapshot without opening TFC GUI
- Foundation for future dashboard panels

## Future Work

Documented in ADRs as possibilities:
- Additional dashboard panels (recent cost trends, policy violations)
- Resource-change counts in snapshot
- Apply details in enriched data
- Real-time activity monitoring enhancements

## Files Changed

### Architecture
- `docs/architecture/ADR-001-workspace-dashboard-design.md` (new)
- `docs/architecture/ADR-002-run-model-enrichment.md` (new)
- `docs/architecture/ADR-003-api-include-parameters.md` (new)
- `docs/architecture/ADR-004-workspace-dashboard-testing.md` (new)
- `docs/architecture/README.md` (new)

### Tests
- `tests/features/workspace_dashboard.feature` (new)

### Implementation
(All already in main via PR #38; no additional changes needed)

## Branch Commits

```
853306a test(bdd): add workspace-dashboard feature specification
b2228bc docs(architecture): add ADRs for workspace-dashboard feature
458514a feat(api,cli): foundational models, API consolidation, and robustness enhancements (#38)
```

## Ready for PR Review

This branch is ready to be merged into main. It adds comprehensive architectural documentation and BDD specification for the workspace-dashboard feature that was implemented in PR #38.

**Recommended PR Description:**

```
feat(docs): add workspace-dashboard ADRs and BDD specification

Documents architectural decisions for the workspace activity dashboard feature:
- ADR-001: Dashboard composition pattern and API optimization
- ADR-002: Run model enrichment via included resources
- ADR-003: API include parameter design with pagination compatibility
- ADR-004: BDD testing strategy (specification-level per Adzic/Farley)

Adds BDD feature file specifying dashboard behavior from business perspective:
- Health status display based on run outcome
- Active run count calculation
- VCS commit metadata rendering
- JSON output snapshot structure

Feature fully implemented in PR #38; this branch adds documentation +
specification per TDD/BDD best practices.

410 tests pass, all linting clean, coverage >67%.
```
