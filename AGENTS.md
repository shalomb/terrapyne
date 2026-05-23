# Terrapyne Agent Instructions

A Python CLI wrapper around Terraform Cloud with a focus on clean code, lean principles, and test-driven development.

## Quick Start

```bash
uv sync                         # Install dependencies (includes dev)
uv run pytest                   # Run all tests (target: 65% coverage)
uv run ruff check . && uv run ruff format .  # Lint and format
uv run mypy src/                # Type check
```

## Detailed Agent Guidelines

This file uses progressive disclosure. For detailed instructions on how agents should operate within this codebase, please refer to the following critical guides:

- **[Agent Workflow Guide](file:///home/unop/shalomb/terrapyne/docs/how-to/agent-workflow.md)** — **CRITICAL**: The strict BDD/TDD Red-Green-Refactor cycle, ACP commit protocol, and mandatory Adversarial Review (Bart) rules.
- **[Python & Testing](file:///home/unop/shalomb/terrapyne/docs/how-to/python-and-testing.md)** — Type hints, imports, test structure, pytest-bdd patterns.
- **[BDD Specifications](file:///home/unop/shalomb/terrapyne/docs/explanation/bdd-specifications.md)** — Writing Adzic-aligned feature files and step definitions.
- **[Commits & Review](file:///home/unop/shalomb/terrapyne/docs/how-to/commits-and-review.md)** — Atomic commits, conventional format, PR process.
- **[Architecture](file:///home/unop/shalomb/terrapyne/docs/explanation/architecture/)** — ADRs, design decisions, model patterns.

## Essential Skills

Use these skills to stay aligned:

| Skill | When to Use |
|-------|------------|
| [git](~/.claude/skills/git/) | Before any git operation — read safety guardrails |
| [adzic-index](~/.claude/skills/adzic-index/) | Evaluating BDD feature file quality against spec principles |
| [farley-index](~/.claude/skills/farley-index/) | Auditing test suite health: fast, honest, necessary, maintainable, atomic, repeatable |
| [test-accordion](~/.claude/skills/test-accordion/) | Expanding/contracting test scope in elastic loop during TDD |
| [using-git-worktrees](~/.claude/skills/using-git-worktrees/) | Creating isolated feature branches with worktrees |
| [commit](~/.claude/skills/commit/) | Crafting atomic, verified commits before pushing |
