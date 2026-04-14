# Commits & Review Guide

Atomic commits, conventional formats, and PR process for Terrapyne.

## Atomic Commit Protocol (ACP)

Every commit is:
- **Self-contained**: Solves one problem, stands alone
- **Verified**: Passes tests, linting, type checks locally before push
- **Meaningful**: Clear commit message explains *why*

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`
**Scope:** Optional; affected area (e.g., `workspace-cmd`, `run-model`, `cli`)
**Subject:** Imperative, present tense, lowercase, no period, ≤50 chars

**Good examples:**
```
feat(workspace-cmd): show health status in workspace snapshot

fix(runs): prevent Run ID truncation in table output

test(workspace-dashboard): add BDD scenarios for activity snapshot

docs(adr): add ADR-004 for workspace dashboard testing strategy

refactor(api-client): consolidate workspace_show API calls

chore: update pytest to 8.0.0
```

**Bad examples:**
```
feat: Added workspace health status    # Vague scope, past tense
Fixed bug in run display               # Missing type
WIP: workspace changes                 # No type/scope
Update dependencies                    # No meaningful detail
```

### Commit Body

Explain *why* the change matters, not *what* changed (the diff shows that).

**Example:**
```
feat(workspace-cmd): show health status in workspace snapshot

The workspace show command now displays a health and activity summary 
including latest run status, active run count, and VCS metadata. This 
gives DevOps engineers a quick assessment without opening the GUI.

- Fetch last 20 runs in single API call (reduces latency)
- Determine health from latest run status
- Display commit metadata if run is VCS-linked
- JSON output includes snapshot section for IDP integration

Closes #42
Relates to ADR-001 (Workspace Dashboard Architecture)
```

### Commit Size

- **Too small**: "Add import statement" (combine with feature commit)
- **Too large**: Multiple unrelated features (split them)
- **Right size**: One logical unit that could be reverted independently

**Test:** If your commit message uses "and" more than once, it's probably too large.

## Using the `/commit` Skill

Before pushing, use the `/commit` skill to craft safe, verified commits:

```bash
# In Claude Code:
/commit
```

The skill:
1. Runs `git status` to see changes
2. Runs `git diff` to review staged changes
3. Runs `git log` to follow the repo's commit style
4. Drafts a commit message
5. Creates the commit (verifying tests pass)
6. Runs `git status` to confirm

**Never skip the skill** — it's your safety net against bad commits.

## Pre-Push Checklist

Before `git push`:

```bash
# 1. Run tests (all must pass)
uv run pytest

# 2. Check coverage (≥65%)
uv run pytest --cov=terrapyne --cov-fail-under=65

# 3. Lint and format
uv run ruff check . && uv run ruff format .

# 4. Type check
uv run mypy src/

# 5. Review commits locally
git log origin/main..HEAD --oneline

# 6. Ensure no AI markers in code/commits
grep -r "Co-Authored-By\|claude\|openai" src/ tests/  # Should be empty
```

All must pass before pushing.

## Pull Request Process

1. **Create worktree** for isolated work:
   ```bash
   # Use /using-git-worktrees skill
   git worktree add .claude/worktrees/feature-name
   ```

2. **Write tests first** (Red/Green TDD):
   - Feature file (BDD) or unit test
   - Should fail initially
   - Implement minimal code to pass

3. **Commit frequently**:
   - One atomic commit per logical unit
   - Use `/commit` skill for safety
   - All tests pass locally

4. **Push and create PR**:
   ```bash
   git push -u origin feature-branch
   # GitHub creates PR with branch name as title
   ```

5. **PR Description** (auto-filled with git commits):
   - Summary: 1-3 bullet points of impact
   - Test plan: How reviewers should verify
   - Links: Related ADRs, issues, related PRs
   - **No AI markers** (no "Co-Authored-By", no "Claude Code", no "AI-generated")

   **Example:**
   ```
   ## Summary
   - Workspace show command now displays health snapshot
   - Reduces API calls by combining run fetch into single request
   - Enables IDP integration via JSON output

   ## Test Plan
   - [ ] Run `pytest tests/test_cli/test_workspace_dashboard_bdd.py`
   - [ ] Manual: `terrapyne workspace show my-app-dev`
   - [ ] Verify JSON output includes snapshot section

   Related: ADR-001 (Workspace Dashboard Architecture)
   ```

6. **Review & merge**:
   - Code review focuses on intent, clarity, adherence to patterns
   - Style issues caught by pre-commit hooks (not manual review)
   - Merge to `main` when approved

## Branch Naming

```
feat/<feature-name>           # New feature
fix/<issue-name>              # Bug fix
docs/<doc-name>               # Documentation
refactor/<area-name>          # Refactoring
test/<test-name>              # Test coverage
chore/<maintenance-task>      # Maintenance
```

**Good examples:**
```
feat/workspace-health-snapshot
fix/run-id-truncation
docs/bdd-specifications
refactor/api-client-consolidation
test/workspace-dashboard-bdd
```

## Code Review Checklist

Reviewers should verify:

- [ ] All tests pass (CI green)
- [ ] Coverage ≥65% (or improved from before)
- [ ] Type checks pass (`mypy`)
- [ ] Linting passes (`ruff`)
- [ ] Commit messages are clear and follow conventions
- [ ] No AI markers in code or commits
- [ ] Feature aligns with related ADRs
- [ ] BDD scenarios are outcome-focused (if applicable)
- [ ] No speculative features (only what was requested)

## After Merge

1. **Delete worktree**:
   ```bash
   git worktree remove .claude/worktrees/feature-name
   ```

2. **Close related issues** (via PR comment or GitHub automation)

3. **Update documentation** if needed:
   - ADRs if architectural decision changed
   - TODO.md if discovery findings apply
   - Contributing guides if new patterns introduced

## Common Patterns

### Squashing Commits Before Merge

If review feedback requires changes:
```bash
# Make fixes
git add .
git commit -m "fix: address review feedback"

# Squash with previous commit (if related)
git rebase -i origin/main
# Mark second commit as 'squash'
# Update commit message if needed
git push --force-with-lease
```

### Splitting a Commit

If a commit is too large:
```bash
git rebase -i origin/main
# Mark commit as 'edit'
git reset HEAD~1
# Stage parts selectively
git add <file1>
git commit -m "feat: part 1"
git add <file2>
git commit -m "feat: part 2"
git rebase --continue
```

### Reverting a Merge

If a PR causes issues after merge:
```bash
git revert -m 1 <merge-commit-hash>
git push
```

Creates a new commit that undoes the merge (safe; preserves history).

## Git Safety

**Always use the `/git` skill before any git operation:**
```bash
# In Claude Code:
/git  # Read safety guardrails
```

Key rules:
- Never `git push --force` to `main`
- Never skip hooks (`--no-verify`)
- Never run `git reset --hard` without understanding consequences
- Use `--force-with-lease` instead of `--force` to push safer

---

**Remember:** Every commit is a record of the project's evolution. Take care in crafting them — your future self (and teammates) will thank you.
