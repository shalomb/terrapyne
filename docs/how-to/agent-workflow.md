# Agent Workflow Guide

This guide dictates the mandatory workflow, testing practices, and review steps for all AI agents (e.g., Marge, Ralph, Bart, etc.) operating in the Terrapyne repository.

## Strict BDD and TDD Adherence

All features and changes must be built using strict **Adzic BDD (Behavior-Driven Development)** and **Farley TDD (Test-Driven Development)**.

### The Double-Loop Workflow

1. **Outer Loop (Red BDD)**: Write a failing scenario in `tests/features/*.feature` using Gojko Adzic's Specification by Example principles (outcome-focused, not implementation-scripted).
2. **Inner Loop (Red TDD)**: Write a failing unit test for the supporting model/API in `tests/test_unit/`.
3. **Green TDD**: Write the minimal code to make the unit test pass. Run tests frequently.
4. **Safe ACP Commit**: Once the tests are green, perform an Atomic Commit Protocol (ACP) commit. **Do NOT refactor the messy "Green" state before committing.**
5. **Refactor & Commit**: Refactor the code for clarity, ensure all tests still pass, and then make a second commit containing the clean refactored state. This 2-commit "Green then Refactor" cycle is essential.
6. **Green BDD**: Implement the CLI wrapper/logic to make the outer loop scenario pass.

*Use the `test-accordion` skill to expand and contract test scope during this elastic loop.*

## The Adversarial Review (Bart)

Once the implementation is complete and committed:

1. The change MUST be subjected to an adversarial review by **Bart** (the review agent).
2. Use the `bart` skill to review the code, diff, test output, or PR.
3. **Fixing Issues**: The main agent must fix all *related* issues found by Bart. 
4. **Parking Issues**: Any *unrelated* bugs, smells, or edge cases found by Bart during the review must not be bundled into the current commit/PR. Instead, they must be parked back onto the `TODO.md` backlog for a future iteration.

## Commit Protocol (ACP)

Atomic Commit Protocol (ACP) is **mandatory, not optional**:

1. **One reason to change** — each commit addresses exactly one concern. Split work before committing.
2. **Verified before commit** — the full verification suite must pass locally:
   ```bash
   uv run pytest tests/ --ignore=tests/uat -x -q --no-header --cov=src --cov-report=term
   uv run ruff check src/ tests/
   uv run mypy src/
   ```
3. **Conventional Commits format** — `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
4. **No AI markers** — no co-author lines, no AI attribution anywhere.
5. **Use `/commit` skill** — always use the commit skill to stage, verify, and craft the message.

## Development Worktrees

Always isolate your work. Before beginning an implementation plan:
1. Create a worktree for isolated work using the `using-git-worktrees` skill.
   ```bash
   git worktree add .claude/worktrees/feature-name
   ```

## Continuous Integration

**Pre-commit checks:**
- Ruff (linting, formatting)
- MyPy (type checking)
- Test coverage (≥65%)

**All commits must pass locally before pushing** — no fix-up commits.

## Getting Help

- Architecture decisions: See `docs/explanation/architecture/ADR-*.md`
- Testing strategy: See `docs/explanation/architecture/ADR-004-workspace-dashboard-testing.md` and `docs/explanation/bdd-specifications.md`
- Python patterns: See `docs/how-to/python-and-testing.md`
- Git safety: Use `/git` skill before any operation

---
**Note:** This project enforces clean code and lean principles. Challenge vague requirements; propose alternatives before implementing. No speculative features.
