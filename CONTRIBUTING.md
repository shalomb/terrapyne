# Contributing to Terrapyne

First off, thank you for considering contributing to Terrapyne! It's people like you that make open-source software such a great community.

To ensure the highest quality of the codebase, Terrapyne enforces strict engineering standards. Please read this guide carefully before submitting a pull request to ensure a smooth review process.

## 🛠️ Local Development Setup

Terrapyne uses [`uv`](https://github.com/astral-sh/uv) for fast, reliable dependency management and virtual environments.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/terrapyne.git
   cd terrapyne
   ```

2. **Install `uv`** (if you don't have it):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies and setup the environment:**
   ```bash
   uv sync
   ```

4. **Run the test suite to verify your setup:**
   ```bash
   uv run pytest
   ```

---

## 🧪 Testing Standards (The Non-Negotiables)

We do not accept PRs that lack tests or reduce overall test coverage. We strictly follow two testing philosophies:

### 1. Farley TDD (Red-Green-Refactor)
All bug fixes and low-level features must follow test-driven development:
- **Red:** Write a failing test first. Run it and confirm it fails for the right reason.
- **Green:** Write the *minimal* code necessary to make the test pass.
- **Refactor:** Clean up the code while keeping the tests green.

### 2. Adzic BDD (Specification by Example)
Every **user-visible behavior** (especially CLI commands) must be documented as a Gherkin `.feature` file in `tests/features/`.
- Scenarios must use **real examples**, not vague abstractions.
  - ❌ *Bad:* `When the user runs the command`
  - ✅ *Good:* `When I run tfc state outputs db_endpoint --raw`
- Step definitions live alongside the feature files in the `tests/test_cli/` directory.

To run tests with coverage (minimum 65% required):
```bash
uv run pytest tests/ -x -q --no-header --cov=src --cov-report=term
```

---

## ✍️ Code Quality & Style

Before committing, ensure your code passes our linting and type-checking rules:

```bash
# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

- **Type Hints:** Required for all function signatures. Use Pydantic models for data structures.
- **Docstrings:** Required for all public functions, classes, and methods.

---

## 📦 Atomic Commit Protocol (ACP)

We enforce an Atomic Commit Protocol. Every commit must be:
1. **Self-contained:** Solves exactly one problem.
2. **Verified:** Tests, linting, and type checks pass *on that specific commit*.
3. **Formatted:** Follows [Conventional Commits](https://www.conventionalcommits.org/).

**Format:** `<type>(<scope>): <subject>`

*Examples:*
- `feat(workspace): add health status to show command`
- `fix(runs): prevent Run ID truncation in table output`
- `docs(adr): add ADR for workspace dashboard testing`

Code and its corresponding tests must be in the **same commit**. Never split them.

---

## 🚀 Pull Request Process

1. Create a new branch from `main` (e.g., `feat/your-feature-name`).
2. Make your atomic commits.
3. Push to your fork and open a Pull Request.
4. **Fill out the PR Template completely.**
5. Wait for CI checks to pass and a maintainer to review.

### The Review Process (Meet "Bart")
Terrapyne uses strict automated and manual review guardrails (internally known as our "Bart" persona). Your PR will be evaluated against:
- Are there tests for the new behavior?
- Do the tests actually prove the code works?
- Are errors written to `stderr` and data to `stdout`?
- Are exit codes correct (non-zero on failure)?
- Are credentials handled securely?

If these are not met, the PR will be rejected and sent back for revisions. 

---

Thank you for contributing to Terrapyne!
