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
- **Atomic Commits (ACP)**: Every commit is a single, self-contained unit of verified work — one reason to change, all tests green, linting and type checks pass. Never batch unrelated changes. Never commit broken state.
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

## CLI Quick Reference

Use `uv run terrapyne` (or `tfc` if the alias is set) for all TFC operations. Run `terrapyne <cmd> --help` for flag details.

Global flags: `--quiet`, `--debug`, `--cache-ttl N`

### workspace

| Command | What it does |
|---------|-------------|
| `workspace list [-o ORG] [-s STATUS] [-f FORMAT]` | List workspaces in the org |
| `workspace show [-o ORG] [-f FORMAT]` | Show details for current workspace |
| `workspace health [-o ORG]` | Health check for current workspace |
| `workspace vcs [-o ORG]` | Show VCS config for current workspace |
| `workspace variables [-o ORG]` | List workspace variables |
| `workspace var-set -k KEY -v VALUE [-c] [-d DESC] [-o ORG]` | Set a workspace variable (`-c` = sensitive) |
| `workspace var-rm [-o ORG]` | Remove workspace variables |
| `workspace var-copy SOURCE TARGET [-o ORG]` | Copy variables between workspaces |
| `workspace open [-o ORG]` | Open workspace in browser |
| `workspace create NAME [-o ORG] [-p PROJECT] [--tf-version VER] [-m EXEC_MODE] [--working-dir DIR] [--vcs-repo REPO] [--oauth-token-id ID]` | Create workspace |
| `workspace clone SOURCE TARGET [--vcs-token TOK] [-o ORG] [--hostname HOST]` | Clone workspace |
| `workspace delete NAME [-o ORG]` | Delete workspace |
| `workspace costs [-o ORG] [-f FORMAT]` | Show cost estimates |
| `workspace triggers list [-o ORG]` | List VCS triggers |
| `workspace triggers add -s SOURCE [-o ORG]` | Add VCS trigger |
| `workspace triggers remove -t TRIGGER_ID [-o ORG]` | Remove VCS trigger |

> **Note**: `--hostname` only works on `workspace clone`. All other commands read the hostname from `terraform.tf` auto-detection but do not currently accept an explicit `--hostname` flag (B16/B17 — use `TFC_HOSTNAME` env var as workaround once implemented).

### run

| Command | What it does |
|---------|-------------|
| `run list [-w WORKSPACE] [-o ORG] [--status STATUS] [-n LIMIT] [-f FORMAT]` | List recent runs |
| `run show RUN_ID [-o ORG] [-f FORMAT]` | Show run details |
| `run plan [-w WORKSPACE] [-o ORG] [-m MSG] [--wait/--no-wait] [--refresh-only]` | Trigger a confirmable queued plan |
| `run logs RUN_ID [-o ORG] [--stage plan\|apply]` | Show plan or apply logs |
| `run apply [RUN_ID] [-w WORKSPACE] [-o ORG] [-m COMMENT] [--wait/--no-wait]` | Apply a planned run (or trigger new auto-apply run) |
| `run errors [PROJECT] [-o ORG] [-d DAYS] [-n LIMIT] [--json]` | Find recent errored runs |
| `run trigger [WORKSPACE] [-o ORG] [-m MSG] [--auto-apply] [--destroy] [--refresh-only] [--target ADDR] [--replace ADDR] [--wait/--no-wait] [--wait-queue] [--discard-older] [--auto-approve] [--max-wait SEC] [--debug-run] [--speculative]` | Trigger run with queue management |
| `run watch RUN_ID [-o ORG] [--auto-apply] [-m COMMENT] [--max-wait SEC]` | Watch existing run; optionally auto-apply |
| `run follow RUN_ID [-o ORG] [--max-wait SEC]` | Stream run logs in real-time |
| `run discard RUN_ID [-o ORG] [-m REASON]` | Discard a run |
| `run parse-plan [PLAN_FILE\|-] [-f FORMAT] [-o OUTPUT] [-v]` | Parse plain-text plan output |

### state

| Command | What it does |
|---------|-------------|
| `state list [-o ORG] [-n LIMIT]` | List state versions |
| `state show [-w WORKSPACE] [-o ORG]` | Show current state version |
| `state pull [-w WORKSPACE] [-o ORG]` | Pull state JSON |
| `state outputs [-w WORKSPACE] [-o ORG] [-f FORMAT]` | Show state outputs |

### project

| Command | What it does |
|---------|-------------|
| `project list [-o ORG] [-n LIMIT] [-f FORMAT]` | List projects |
| `project find PATTERN [-o ORG] [-n LIMIT]` | Find projects by pattern |
| `project show [-o ORG] [-f FORMAT]` | Show current project |
| `project teams [-o ORG]` | List teams with access to project |
| `project costs NAME [-o ORG] [-f FORMAT]` | Show project cost estimates |

### team

| Command | What it does |
|---------|-------------|
| `team list [-o ORG] [-n LIMIT] [-s SEARCH] [-f FORMAT]` | List teams |
| `team show TEAM_ID [-o ORG]` | Show team details |
| `team create -n NAME [-d DESC] [-o ORG]` | Create team |
| `team update TEAM_ID [-n NAME] [-d DESC] [-o ORG]` | Update team |
| `team delete TEAM_ID [-o ORG]` | Delete team |
| `team members TEAM_ID [-o ORG]` | List team members |
| `team add-member TEAM_ID -u USER [-o ORG]` | Add member to team |
| `team remove-member TEAM_ID -u USER [-o ORG]` | Remove member from team |

### vcs / varset / debug

| Command | What it does |
|---------|-------------|
| `vcs list [-o ORG]` | List VCS providers |
| `vcs repos [-o ORG]` | List VCS repos |
| `vcs show [-o ORG]` | Show VCS provider details |
| `varset list [-o ORG]` | List variable sets |
| `varset show NAME [-o ORG]` | Show variable set |
| `varset apply NAME -w WORKSPACE [-o ORG]` | Apply varset to workspace |
| `varset remove NAME -w WORKSPACE [-o ORG]` | Remove varset from workspace |
| `debug run` | Dump run debug info |
| `debug workspace` | Dump workspace debug info |

### Context auto-detection

When run inside a Terraform project with a `backend "remote"` or `cloud` block in `.tf` files, terrapyne auto-detects `organization` and `workspace`. Omit `-o`/`-w` flags in those cases.

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

Atomic Commit Protocol (ACP) — **mandatory, not optional**:

1. **One reason to change** — each commit addresses exactly one concern (feature slice, bug fix, doc update, refactor). Split work before committing, never after.
2. **Verified before commit** — the full verification suite must pass locally:
   ```bash
   uv run pytest tests/ --ignore=tests/uat -x -q --no-header --cov=src --cov-report=term
   uv run ruff check src/ tests/
   uv run mypy src/
   ```
3. **Conventional Commits format** — `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` — message describes *why*, not *what*
4. **No AI markers** — no co-author lines, no AI attribution anywhere
5. **Use `/commit` skill** — always use the commit skill to stage, verify, and craft the message

A commit that breaks tests, bundles unrelated changes, or skips verification is a protocol violation. Revert it.

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

6. Commit & push (ACP — see Commits & PRs section):
   - Use `/commit` skill — mandatory, runs verification before committing
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
