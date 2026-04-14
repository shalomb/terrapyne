# Development Guides

Detailed conventions and workflows for Terrapyne development.

## Quick Links

- **[Python & Testing](python-and-testing.md)** — Type hints, imports, test structure, pytest-bdd patterns
- **[BDD Specifications](../explanation/bdd-specifications.md)** — Writing Adzic-aligned feature files and step definitions
- **[Commits & Review](commits-and-review.md)** — Atomic commits, conventional format, PR workflow

## For Agents

Start with the relevant guide based on your task:

| Task | Guide |
|------|-------|
| Writing tests or features | [BDD Specifications](../explanation/bdd-specifications.md) + [Python & Testing](python-and-testing.md) |
| Python code (models, CLI, utils) | [Python & Testing](python-and-testing.md) |
| Creating commits or PRs | [Commits & Review](commits-and-review.md) |
| Understanding project structure | [AGENTS.md](../../AGENTS.md) + architecture in `../explanation/architecture/` |

## Skills to Use

These guides link to Claude Code skills:
- **adzic-index** — Audit BDD feature file quality
- **farley-index** — Audit test suite health
- **test-accordion** — Expand/contract test scope elastically
- **git** — Safety guardrails before git operations
- **commit** — Craft safe, verified commits
- **using-git-worktrees** — Create isolated feature branches

See [AGENTS.md](../../AGENTS.md) for skill details.

## Development Workflow

1. Create a worktree: `/using-git-worktrees`
2. Write failing test (Red): Feature file or unit test
3. Make it pass (Green): Minimal implementation
4. Refactor (optional): Improve clarity
5. Commit: `/commit` skill
6. Push & create PR

See [Commits & Review](commits-and-review.md) for detailed workflow.
