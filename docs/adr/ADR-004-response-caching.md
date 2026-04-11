# ADR-004: File-based Response Caching

## Status
Accepted

## Context
Listing workspaces, projects, or teams in large TFC organizations can be slow due to API latency and pagination requirements. Users often run commands like `workspace show` or `project show` repeatedly, leading to redundant network traffic.

## Decision
We decided to implement a local, file-based response cache in `~/.cache/terrapyne/` with a default 5-minute TTL and automatic invalidation on any write (POST/PATCH/DELETE) operation.

## Rationale (Y-Statement)
In context of repeated read-heavy CLI usage,
facing high API latency for list operations,
we decided for a transparent file-based cache
to achieve sub-second response times for cached queries,
accepting that users must occasionally wait for cache expiration if external changes occur (mitigated by explicit write invalidation).

## Consequences
+ Near-instant response for repeated `show` and `list` commands
+ Reduced TFC API load and risk of rate-limiting
+ "Offline-ish" support for recently fetched data
- Potential for stale data if changes are made outside of `terrapyne` (e.g., via TFC UI)

## Alternatives Considered
- **In-memory caching**: Rejected as it does not persist across separate command invocations.
- **Aggressive 0-TTL cache**: Rejected as it provides no performance benefit.
