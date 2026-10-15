# CLI Command Hierarchy & Surface Design

Canonical standard for CLI taxonomy, command grouping, and surface design. Cited from `docs/how-to/agent-workflow.md`, `AGENTS.md`, and the Marge, Lisa, Ralph, and Bart agent personas.

---

## Why This Standard Exists

CLI inconsistency is frustrating for humans, but it is **fatal for AI coding agents**. 

When commands are asymmetrical — for example, updating a repository via `tfc vcs set-repo`, updating a branch via `tfc workspace set-branch`, and updating a working directory via `tfc workspace update --working-dir`:
1. **Agents Hallucinate**: LLMs infer symmetrical command patterns (e.g. guessing `tfc workspace set-repo` or `tfc vcs set-branch`). When those fail, agents enter costly trial-and-error retry loops.
2. **Discovery Multiplies**: Agents are forced to execute extra discovery steps (`--help` scans) across multiple disparate groups instead of inspecting the logical parent resource.
3. **Scripts Break**: Automation pipelines and shell scripts cannot easily compose commands or reuse parameter patterns.

This standard establishes clear, immutable architectural rules for organizing commands, subcommands, and options in the `tfc` CLI.

---

## Principle 1 — Strict Scope Separation (Organization vs. Resource)

Commands must be grouped by the **scope of the entity being acted upon**, not by convenience or technology name.

| Scope | Rule | Canonical Top-Level Groups | Examples |
|---|---|---|---|
| **Organization-Level** | Assets, integrations, catalog discoveries, and settings that belong to the organization as a whole and are not tied to any single workspace. | `tfc vcs`<br>`tfc team`<br>`tfc project` | `tfc vcs list`<br>`tfc vcs repos`<br>`tfc team list` |
| **Resource-Level** | Specific operational resources that have their own lifecycle, state, and attributes within an organization. | `tfc workspace`<br>`tfc run`<br>`tfc varset`<br>`tfc state` | `tfc workspace show`<br>`tfc workspace update`<br>`tfc run trigger` |

### The Scope Rule

> **Never place a resource-scoped mutation or query under an organization-scoped command group.**

* **Bad**: `tfc vcs set-repo <workspace> <identifier>` *(modifies a workspace, but placed under `vcs`)*
* **Bad**: `tfc vcs show <workspace>` *(inspects a workspace, but placed under `vcs`)*
* **Good**: `tfc workspace update <workspace> --repo <identifier>`
* **Good**: `tfc workspace vcs show <workspace>`
* **Good**: `tfc vcs list -o <org>` *(lists OAuth connections for the organization)*

---

## Principle 2 — Backend API Parity (Single-Shot Attribute Updates)

The Terraform Cloud REST API updates workspace configuration via a single atomic endpoint: `PATCH /api/v2/workspaces/:id`. That endpoint accepts attributes such as `name`, `terraform-version`, `execution-mode`, `working-directory`, and the `vcs-repo` object (`identifier`, `branch`, `oauth-token-id`, `ingress-submodules`).

### The Atomic Mutation Rule

> **If the backend entity manages attributes via an atomic update endpoint, the CLI's primary `update` command MUST support mutating any combination of those attributes via flags in a single command invocation.**

`tfc workspace update <workspace>` is the canonical mutation command for all workspace configuration:

```bash
tfc workspace update <workspace> \
  [--repo <owner/repo>] \
  [--branch <branch>] \
  [--working-dir <dir>] \
  [--tf-version <version>] \
  [--execution-mode <mode>] \
  [--project <name|id>] \
  [--name <new-name>] \
  [--dry-run]
```

### Anti-Pattern: Scattered Top-Level Verbs

Do **not** invent one-off top-level verbs on `workspace` for single attribute changes.
* **Bad**: `tfc workspace set-branch <workspace> <branch>`
* **Bad**: `tfc workspace set-working-dir <workspace> <dir>`
* **Bad**: `tfc workspace set-repo <workspace> <repo>`
* **Good**: Use flags on `tfc workspace update`, or use the focused sub-typer if sub-resource operations require it.

---

## Principle 3 — Subgroup Symmetry for First-Class Sub-Resources

When a resource owns a collection of sub-resources or complex nested entities, manage them through a **dedicated subcommand group (sub-typer)** directly under the parent resource.

Terrapyne enforces three canonical subgroups under `tfc workspace`:

| Subgroup | Responsibility | Canonical Actions |
|---|---|---|
| `tfc workspace var` | Workspace environment and Terraform variables | `list`, `set`, `remove`, `copy` |
| `tfc workspace triggers` | Upstream run trigger dependencies | `list`, `add`, `remove` |
| `tfc workspace vcs` | VCS repository integration and branch bindings | `show`, `set`, `detach` |

### Verb Uniformity Across Subgroups

Subgroups must share uniform lifecycle verbs:
* **Inspect**: `show` (for a single resource/configuration) or `list` (for a collection).
* **Mutate / Attach**: `set` (or `add` for collections).
* **Delete / Disconnect**: `remove` (or `detach` for integrations).

```
tfc workspace
├── update                     # Atomic multi-attribute updates
├── vcs                        # Focused VCS integration sub-typer
│   ├── show <ws>              # View VCS details (replaces 'vcs show' and 'workspace vcs')
│   ├── set <ws> [flags]       # Set/repoint VCS repo, branch, working-dir
│   └── detach <ws>            # Disconnect VCS from workspace
├── var                        # Variables sub-typer
│   ├── list <ws>
│   ├── set <ws> [flags]
│   ├── remove <ws> [flags]
│   └── copy <src> <dest>
└── triggers                   # Run triggers sub-typer
    ├── list <ws>
    ├── add <ws> [flags]
    └── remove <ws> [flags]
```

---

## Principle 4 — Zero-Guesswork Discoverability for Agents

AI agents and automated tooling navigate CLI tools by requesting `--help` at each level. The taxonomy must follow these discoverability rules:

1. **Every Level Has `--help`**: Root, command groups, sub-typers, and leaf commands must all display clean, formatted help text with command examples.
2. **Consistent Flag Naming**:
   * `--format json` / `-f json`: Universal structured output flag.
   * `--dry-run`: Preview changes without sending API mutations.
   * `--yes` / `-y` or `--force` / `-f`: Non-interactive bypass for confirmations.
   * `--organization` / `-o`: TFC organization override (auto-detected if omitted).
   * `--quiet` / `-q`: Suppress human UI decoration, printing only machine data.
3. **No Hidden Surprises**: Deprecated legacy aliases must be marked `hidden=True` in Typer so they do not clutter `--help` listings seen by agents, but still function when called by older scripts.

---

## Principle 5 — Safe Deprecation and Migration Policy

When consolidating or reorganizing commands:
1. **Never Break Instantly**: Provide a migration path for existing scripts and CI workflows.
2. **Hidden Aliases with Hints**: Maintain the old syntax as a hidden command. When invoked in interactive/human mode, print a warning to `stderr` pointing to the new canonical syntax:
   ```text
   warning: 'tfc vcs set-repo' is deprecated; use 'tfc workspace update --repo' or 'tfc workspace vcs set' instead.
   ```
3. **Documented in CHANGELOG and Migration Guides**: Explicitly log the canonical replacement in `docs/reference/cli-reference.md`.

---

## Bart's Adversarial Review Rubric (CLI Surface Checklist)

When a pull request introduces or modifies a CLI command, Bart evaluates the diff against this rubric. Violations of **Blocker** items prevent merge.

| # | Check | Requirement | Severity if Violated |
|---|---|---|---|
| **C1** | **Scope Separation** | Does any workspace mutation or inspection live under an organization-level command group (e.g. `vcs`, `team`)? | `BLOCKER` |
| **C2** | **Update Symmetry** | Did the PR create a one-off `set-<attr>` verb on `workspace` instead of adding a flag to `workspace update`? | `BLOCKER` |
| **C3** | **Subgroup Symmetry** | If adding a sub-resource command, does it follow the established sub-typer pattern (`workspace var`, `workspace triggers`, `workspace vcs`) and use canonical verbs? | `BLOCKER` |
| **C4** | **Automation Contract** | Does every new/modified command support `--format json`? Does machine data go to `stdout` and human text to `stderr`? | `BLOCKER` |
| **C5** | **Non-Interactive Bypass** | Does any interactive confirmation prompt provide a `--yes`/`-y` or `--force` bypass flag? | `BLOCKER` |
| **C6** | **Actionable Errors** | Do error messages specify What failed, Why, and What command to try next? | `CRITICAL` |
| **C7** | **Legacy Aliases** | Are deprecated commands marked `hidden=True` with deprecation notices to stderr? | `MINOR` |
