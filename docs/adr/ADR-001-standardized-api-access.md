# ADR-001: Standardized API Access Pattern

## Status
Accepted

## Context
Initially, CLI commands manually instantiated API classes (e.g., `WorkspaceAPI(client)`). This led to repetitive setup code and made it harder to manage global concerns like caching or debug tracing across all API calls.

## Decision
We decided to expose API namespaces as properties on the main `TFCClient` class.

## Rationale (Y-Statement)
In context of extending the TFC SDK,
facing repetitive boilerplate and inconsistent API instantiation,
we decided for client-managed API properties
to achieve a cleaner, discoverable developer experience,
accepting slightly tighter coupling between the client and its API sub-modules.

## Consequences
+ Discoverable API (e.g., `client.workspaces.list()`)
+ Centralized control of client-wide settings (debug, cache)
+ Reduced boilerplate in CLI command implementation
- Circular import risks if not carefully managed (addressed via type-hinting guards)

## Alternatives Considered
- **Dependency Injection**: Rejected as overkill for a CLI application.
- **Standalone API functions**: Rejected as it makes state management (auth, base URL) more cumbersome.
