# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for major design decisions in the terrapyne project.

## ADRs for Workspace Dashboard Feature (feat/workspace-dashboard)

### [ADR-001: Workspace Dashboard Architecture](ADR-001-workspace-dashboard-design.md)
Describes the overall design of the workspace health & activity snapshot feature, including:
- Composition pattern: dashboard wraps detail + snapshot + variables + VCS config
- Optimized API fetching: single call for latest run + active count
- Graceful degradation when run data unavailable

**Key decisions:**
- Use `render_workspace_dashboard()` that composes existing renderers
- Fetch 20 recent runs to get both latest run (commit info) and activity snapshot
- Dedicated count call only if workspace has >20 active runs (rare edge case)
- Include "configuration-version" in default list call includes

### [ADR-002: Run Model Enrichment Patterns](ADR-002-run-model-enrichment.md)
Documents how the Run model extracts metadata from included TFC API resources, focusing on:
- Construction-time hydration via `from_api_response(included=...)`
- Safe extraction of commit info from `configuration-version` includes
- Pattern for future enrichments (resource counts, apply details)

**Key decisions:**
- Enrich Run model at construction time, not via lazy properties
- Accept optional `included` parameter in `from_api_response()`
- Gracefully handle missing includes (fields remain None)
- Centralizes enrichment logic in one place

### [ADR-003: API Include Parameters and Pagination Compatibility](ADR-003-api-include-parameters.md)
Specifies how include parameters are added to API methods while preserving pagination:
- Explicit `include` parameter on `list()` and `get()` methods
- Default includes sensible ("configuration-version,plan")
- Overridable by callers for minimal responses
- Works alongside pagination without conflicts

**Key decisions:**
- Include parameters passed as URL query params
- Default includes cover 90% of use cases
- Callers can override with `include=None` or custom string
- No method explosion; one list() method handles all cases

### [ADR-004: Workspace Dashboard BDD Testing Strategy](ADR-004-workspace-dashboard-testing.md)
Documents specification-level BDD testing approach following Adzic/Farley practices:
- Tests describe business outcomes, not implementation
- Feature scenarios focus on "health is visible," not "emoji renders"
- Resilient to refactoring (emoji/color change won't break tests)
- Separate unit tests for component-level behavior

**Key decisions:**
- Use Gherkin to specify feature outcomes
- Mock TFCClient at BDD level
- Avoid assertions on emoji/colors; test presence instead
- Implement step definitions with `Mock(spec=...)` for type safety

---

## General Guidelines for ADRs

When proposing a new ADR:

1. **Use the template:** See any ADR above for structure (Context, Decision, Alternatives, Consequences)
2. **Name descriptively:** ADR-NNN-short-title-kebab-case.md
3. **Link related ADRs:** Reference other decisions at the bottom
4. **Include alternatives:** Document why you chose A over B/C/D
5. **Focus on trade-offs:** What are you gaining? What are you giving up?
6. **Date and status:** Add date and Proposed/Accepted/Deprecated status

## Viewing Status

- **Proposed:** Under consideration; not yet implemented
- **Accepted:** Implemented; stable
- **Deprecated:** Superseded by newer ADR; old decision no longer in use
- **Retired:** No longer relevant to codebase

## Related Files

- Implementation plan: `/home/unop/.claude/plans/foamy-gathering-ullman.md`
- Feature branch: `feat/workspace-dashboard` (derived from workspace-enrichment)
- Key source files:
  - `src/terrapyne/models/run.py` — Run model with enrichment fields
  - `src/terrapyne/api/runs.py` — RunsAPI with include parameter
  - `src/terrapyne/cli/workspace_cmd.py` — workspace show command
  - `src/terrapyne/utils/rich_tables.py` — render_workspace_dashboard()
  - `tests/features/workspace_dashboard.feature` — BDD specification
  - `tests/test_cli/test_workspace_dashboard_bdd.py` — BDD test implementation
