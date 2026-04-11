# TODO — Exploratory Testing Findings

Bugs and improvements found during exploratory testing against live TFC.

## Development Requirements
All new features and fixes must strictly follow:
1. **Red/Green TDD**: Write a failing test first, make it pass with minimal code, then refactor.
2. **Adzic BDD**: Use Gojko Adzic's Specification by Example principles to write `.feature` files.
3. **ACP (Atomic Commit Protocol)**: Every commit must be atomic, verified, and use Conventional Commits.

## Test Environment
For evaluating live TFC behavior, use the following workspace directory:
- `/home/unop/oneTakeda/terraform-dce-developer-ShalomBhooshi/iac/dev`

## Priority Matrix (WSJF-based)

**Impact (Value)**: 🔴 High (4), 🟡 Medium (2), 🟢 Low (1)
**Effort (Size)**: S (1), M (2), L (3)
**Score (WSJF)**: Impact / Effort

| # | Finding | Impact | Effort | Score | Status |
|---|---|---|---|---|---|
| 17 | [BLOCKER] Restore test coverage to 65% (PR #36 Regression) | 🔴 | S | 4.0 | ✅ |
| 18 | [BLOCKER] Fix Cost Estimate Regression (PR #36 logic error) | 🔴 | S | 4.0 | ✅ |
| 19 | [BLOCKER] Remove broad exception silencing in `workspace_cmd.py` | 🔴 | S | 4.0 | ✅ |
| 10 | `--wait` flag for `run trigger`/`apply` to stream logs & exit w/ code | 🔴 | M | 2.0 | TODO |
| 14 | Restore test coverage minimum `fail-under` to 80% (Long-term goal) | 🔴 | M | 2.0 | TODO |
| 20 | [MINOR] Use `RunStatus` enum instead of hardcoded strings | 🟡 | S | 2.0 | ✅ |
| 9 | `--raw` flag for `state outputs` for single unquoted values | 🟡 | S | 2.0 | ✅ |
| 13 | `--json` full structured output for `workspace show` and `project show` | 🟡 | S | 2.0 | TODO |
| 21 | [MINOR] Consolidate `workspace_show` API calls (Optimization) | 🟡 | M | 1.0 | ✅ |
| 22 | [MINOR] Add strict validation to `Run.from_api_response` | 🟡 | M | 1.0 | ✅ |
| 6 | `--debug` flag for API call tracing | 🟡 | M | 1.0 | TODO |
| 1c | `tfc project show` 'single glance' snapshot | 🟡 | M | 1.0 | TODO |
| 8 | Local file-based response cache | 🟢 | L | 0.3 | TODO |

## Task Details (Intent, Context, Success Criteria)

### 17. Restore Test Coverage Threshold (🏆)
**Intent**: Re-establish the quality gate for the codebase after a temporary drop during feature development.
**Context**: PR #36 dropped coverage threshold from 65% to 25%. This masks untested code in the new enrichment feature.
**Success Criteria**: `pyproject.toml` has `cov-fail-under=65` and all tests pass with coverage verification.

### 18. Fix Cost Estimate Regression (🏆)
**Intent**: Ensure the "latest cost estimate" logic is robust against pending or failed runs.
**Context**: PR #36 changed `get_latest_cost_estimate` to only look at the single latest run. If that run hasn't finished cost estimation, it returns `None`.
**Success Criteria**: The logic searches the last ~10 runs for a finished cost estimate, restoring the behavior that allowed users to see the most recent valid cost data even if a new run is in progress.

### 19. Remove Broad Exception Silencing (🏆)
**Intent**: Prevent "silent failures" in the CLI and improve observability for users.
**Context**: `workspace_cmd.py` uses a blanket `except Exception as e` which catches everything from auth errors to network timeouts, merely printing a yellow warning.
**Success Criteria**: Replace with specific exception handling (e.g., `httpx.HTTPStatusError`) and ensure critical failures (like auth) still halt execution or provide clear diagnostic information.

### 20. Use `RunStatus` Enum for Filtering (⭐)
**Intent**: Eliminate magic strings and synchronize CLI filtering with the core domain model.
**Context**: Active run filtering in `workspace_cmd.py` uses a hardcoded comma-separated string of statuses.
**Success Criteria**: The active status list is derived from the `RunStatus` enum, ensuring that any future status changes in the domain model automatically propagate to the CLI.

### 21. Consolidate `workspace_show` API Calls (⭐)
**Intent**: Reduce command latency by minimizing round-trips to the TFC API.
**Context**: Currently, `workspace_show` makes one call for the latest run (including VCS) and another for active counts.
**Success Criteria**: Fetch a window of runs (e.g., 20) in a single call and calculate active counts and latest run details from that single response.

### 22. Strict Validation for `Run` Model (⭐)
**Intent**: Ensure data integrity when consuming external API payloads.
**Context**: `Run.from_api_response` uses `model_construct`, which is fast but skips type/presence validation.
**Success Criteria**: Implement validation for critical fields (id, status) while maintaining the factory pattern for relationship extraction.

---
*(Existing legacy tasks 9, 10, 14, 13, 1c, 6, 8 details remain in the backlog)*
