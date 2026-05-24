# Design Philosophy

Terrapyne was built to solve a specific set of problems encountered by DevOps and Platform Engineers working with Terraform Cloud (TFC) at scale.

## 1. CLI First, UI Second
The Terraform Cloud web interface is excellent for occasional use, but it can be slow and cumbersome for daily, repetitive tasks. Terrapyne's CLI is designed for speed and efficiency in the terminal, where engineers spend most of their time.

## 2. Unix Philosophy: Structured Data
Every command in the `tfc` CLI supports the `--format json` flag. This follows the Unix philosophy of "everything is a file" (or in this case, a stream of data). By providing structured JSON output, we make it trivial to:
- Pipe data into `jq` for advanced filtering.
- Feed TFC state into CI/CD pipelines.
- Provide clean context for AI agents and LLMs.

## 3. High-Level Abstractions
The raw TFC API is a JSON:API implementation that can be verbose. Terrapyne provides high-level abstractions to simplify common workflows:
- **Polling & Waiting**: Instead of writing your own loops to check if a run has finished, the SDK provides `poll_until_complete`.
- **Context Resolution**: The CLI can automatically detect your TFC organization and workspace by looking at local Terraform state files.
- **Bulk Operations**: Commands like `var-copy` and `clone` handle multiple API calls behind the scenes to perform complex tasks in a single step.

## 4. Type Safety with Pydantic
The SDK is built on Pydantic models. This ensures that every piece of data coming from the TFC API is validated and typed. For the developer, this means:
- Autocompletion in your IDE.
- Catching API response changes early.
- Robust data handling without manual dictionary parsing.

## 5. Built for Automation
Terrapyne is not just a CLI; it's a foundation for building your own internal developer portals (IDPs) and custom GitOps bots. The SDK is designed to be embedded in larger systems, handling the "plumbing" of TFC so you can focus on your business logic.

---

## Automation & Agent Contract

The following principles govern how every command must behave. They apply equally to human scripts, CI/CD pipelines, and AI coding agents. New commands that violate these principles should be treated as bugs, not style preferences.

### Output guides the next action
Every command should tell the caller what to do next. A successful mutation prints the ID of the created resource so it can be passed to the next command. A failed run prints the error *and* the corrective command, not just a status code. The goal is zero secondary discovery steps.

### stdout for data, stderr for everything else
Machine-readable output (JSON, raw IDs, state values) goes to stdout. All human-facing output — progress messages, warnings, confirmations, rich tables — goes to stderr (or the Rich console, which respects TTY). This ensures `command | jq` always works without filtering noise.

> **Current status**: Rich's `console.print` writes to stdout by default. This is a known gap (tracked as AX-stdout) — commands should use `Console(stderr=True)` for all non-data output.

### Structured output is a contract, not a convenience
`--format json` is not an afterthought. Every command — including mutations like `workspace create` and `run trigger` — must support it. The JSON envelope must be consistent: a single object for singular resources, an array for lists. No ANSI codes, no truncation, no omitted fields.

### Actionable errors
An error message must contain enough information to act on without issuing another command:
- **What failed**: the resource type and name
- **Why it failed**: the API error title and detail, or the Terraform error block
- **What to try next**: a corrective command or flag hint where possible

A message like `API Error (422)` with no detail is not actionable. A message like `API Error (422): Workspace name already taken — use --ignore-exists to recover` is.

### No interactive requirements
Every interactive prompt must have a non-interactive bypass flag. `--yes` / `-y` for confirmations. `--ignore-exists` for idempotent creates. `--auto-approve` for destructive runs. Any command that blocks on a prompt in a non-TTY context is broken for automation.

### TTY-aware output
Output adapts to its context:
- **TTY**: Rich tables, ANSI colour, progress spinners, truncation for readability.
- **Non-TTY (pipe/redirect)**: Plain text or JSON, no colour, no truncation, no progress output.

Rich handles most of this automatically. Commands must not override it by hardcoding ANSI or assuming terminal width.
