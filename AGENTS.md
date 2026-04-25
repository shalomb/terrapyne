# Terrapyne Agent Instructions

A Python CLI wrapper around Terraform Cloud with a focus on clean code, lean principles, and test-driven development.

## Quick Start

```bash
uv sync                         # Install dependencies (includes dev)
uv run pytest                   # Run all tests (target: 65% coverage)
uv run ruff check . && uv run ruff format .  # Lint and format
uv run mypy src/                # Type check
```

## Core Principles

- **Red/Green TDD**: Write failing tests first, minimal implementation, then refactor
- **Adzic BDD**: Feature files use Gojko Adzic's Specification by Example (outcome-focused, not implementation-scripted)
- **Atomic Commits**: Every commit is verified, self-contained, uses Conventional Commits
- **No AI Markers**: Never add co-author or AI attribution to code, commits, docs, or PR descriptions

## Development Guides

Detailed conventions and patterns:
- [Python & Testing](docs/how-to/python-and-testing.md) — Type hints, imports, test structure, pytest-bdd
- [BDD Specifications](docs/explanation/bdd-specifications.md) — Writing Adzic-aligned feature files and step definitions
- [Commits & Review](docs/how-to/commits-and-review.md) — Atomic commits, conventional format, PR process
- [Architecture](docs/explanation/architecture/) — ADRs, design decisions, model patterns

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

## Project Structure

```
src/terrapyne/
├── cli/          # Typer CLI commands (workspace, run, state, project, etc.)
├── api/          # TFCClient and API abstractions
├── models/       # Pydantic models (Run, Workspace, StateVersion, etc.)
├── core/         # Parsing and core utilities
└── sdk/          # High-level SDK interface

tests/
├── test_cli/     # pytest-bdd step definitions and assertions
├── test_unit/    # Unit tests for models and utilities
├── features/     # Gherkin feature files (.feature)
└── conftest.py   # Shared fixtures
```

## Testing Patterns

**BDD (pytest-bdd):**
- Feature files describe business outcomes: `tests/features/*.feature`
- Step definitions in `tests/test_cli/test_*_bdd.py`
- Use `@given/@when/@then` decorators with parsers
- Mock at TFCClient level, not httpx
- Assert outcomes (e.g., "active run count visible"), not implementation (e.g., "emoji 🟢 present")

**Unit Tests:**
- Models and utilities in `tests/test_unit/`
- Use fixtures and mocks (`Mock(spec=...)` for type safety)
- Fast, deterministic, no I/O

**Coverage:**
- Minimum 65% across `src/terrapyne/`
- Run: `pytest --cov=terrapyne --cov-report=html`

## Code Quality

**Ruff (linting & formatting):**
```bash
ruff check . && ruff format .
```
- Line length: 100 chars
- Target: Python 3.12+
- Rules: E, F, I, B, PL, RUF (see `pyproject.toml` for exceptions)

**MyPy (type checking):**
```bash
mypy src/
```
- Strict mode enabled where possible
- Document any `# type: ignore` with reason

**Pre-commit hooks:**
- Ruff, MyPy, and test coverage validation run automatically
- Fix issues before pushing

## Commits & PRs

- **Format**: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`)
- **Scope**: Single responsibility per commit (atomic)
- **Message**: Describe *why*, not *what* (the diff shows what)
- **Verification**: All commits pass tests, linting, type checks
- **Skill**: Use `/commit` skill to craft safe, verified commits

See [Commits & Review Guide](docs/how-to/commits-and-review.md) for details.

## Development Workflow

1. Create a worktree for isolated work:
   ```bash
   # Skill: using-git-worktrees
   git worktree add .claude/worktrees/feature-name
   ```

2. Write failing test first (Red):
   - Feature file (BDD) or test function (unit)
   - Use `pytest -k <test>` to focus

3. Make test pass (Green):
   - Minimal implementation, no over-engineering
   - Run tests frequently: `pytest --tb=short`
   - Use `test-accordion` skill to expand/contract scope

4. Refactor (optional):
   - Only if code clarity improves
   - Re-run tests; ensure coverage stable

5. Verify — full suite must be green before committing:
   ```bash
   uv run pytest tests/ --ignore=tests/uat -x -q --no-header --cov=src --cov-report=term
   uv run ruff check src/ tests/
   uv run mypy src/
   ```

6. Commit & push:
   - Use `/commit` skill for safe, verified commits
   - Push branch before opening PR: `git push -u origin <branch>`
   - Open PR: `gh pr create --title "..." --body "..." --base main`
   - Fill in every section of `.github/PULL_REQUEST_TEMPLATE.md` in the PR body

7. Review & merge (Bart):
   - Bart reviews the PR adversarially
   - No critical issues → Bart merges: `gh pr merge <number> --squash --delete-branch`
   - Critical issues found → Bart writes them back as a new task list; Ralph resumes a new iteration
   - Ensure no AI markers in code/commits

## Continuous Integration

**Pre-commit checks:**
- Ruff (linting, formatting)
- MyPy (type checking)
- Test coverage (≥65%)

**All commits must pass locally before pushing** — no fix-up commits.

## Getting Help

- Architecture decisions: See `docs/explanation/architecture/ADR-*.md`
- Testing strategy: See ADR-004 and [BDD Specifications guide](docs/explanation/bdd-specifications.md)
- Python patterns: See [Python & Testing guide](docs/how-to/python-and-testing.md)
- Git safety: Use `/git` skill before any operation

---

**Note:** This project enforces clean code and lean principles. Challenge vague requirements; propose alternatives before implementing. No speculative features.
