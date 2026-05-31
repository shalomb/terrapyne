# Terrapyne Improvement Requests — from ASG BB v4.0 session (2026-05-25 to 2026-05-31)

These are friction points encountered while using terrapyne to manage TFC runs
during the ASG Building Block v4.0 E2E testing session. Each item includes the
context of what we were doing, what went wrong, and the ideal outcome.

---

## F1: `run trigger` fails with 404 when workspace was renamed

**Context:** We renamed workspace `tec-dce-inn-dev-93400-asg-bb-test` to
`tec-dce-inn-dev-93400-asg-bb-test-windows`. Subsequent `terrapyne run trigger`
from the repo directory failed with 404 because terrapyne resolves the workspace
name from `terraform.tf` backend config, which still had the old name.

**Workaround:** Used raw `curl` to the TFC API with the workspace ID directly.

**Ideal outcome:** `terrapyne run trigger --workspace-id ws-xxx` flag, or
`--workspace <name>` override that bypasses auto-detection from `terraform.tf`.

---

## F2: `run list` resolves workspace from terraform.tf — no override

**Context:** After creating a new workspace (`tec-dce-inn-dev-93400-asg-bb-test-basic`),
`terrapyne run list` from `examples/basic/` returned "No runs found" because
`terraform.tf` still references the old workspace name.

**Workaround:** Used `curl` with workspace ID.

**Ideal outcome:** `terrapyne run list --workspace-id ws-xxx` or
`terrapyne run list -w <workspace-name>` that overrides auto-detection.

---

## F3: No `run cancel` command

**Context:** Needed to cancel pending runs to unblock the queue. `terrapyne run cancel`
doesn't exist.

**Workaround:** Used `curl -X POST .../runs/{id}/actions/cancel`.

**Ideal outcome:** `terrapyne run cancel <run-id> -m "reason"` — mirrors the
existing `run discard` command.

---

## F4: `run discard` fails on pending runs (409 transition not allowed)

**Context:** Tried to discard pending runs but got 409. Pending runs must be
*cancelled*, not *discarded* (discard is only valid for `cost_estimated` or
`policy_checked` states).

**Workaround:** Used `curl` to call the cancel endpoint.

**Ideal outcome:** `terrapyne run discard` should detect the run state and
automatically use cancel vs discard as appropriate, or at minimum surface a
helpful error: "Run is pending — use `terrapyne run cancel` instead."

---

## F5: `run watch` timeout is too short for agent-pool delays

**Context:** `terrapyne run trigger --auto-apply` timed out after 1800s with
"did not complete within 1800.0s (current status: pending)" because the TFC
agent pool was slow to pick up the job.

**Workaround:** Triggered via API and watched separately.

**Ideal outcome:** `--timeout` flag on `run trigger` and `run watch`, or
infinite wait with Ctrl-C to abort. Default 1800s is too aggressive for
agent-pool execution mode.

---

## F6: No workspace rename/create/clone with agent pool

**Context:** `terrapyne workspace clone` failed with 422 "Agent pool not found"
because the clone operation doesn't properly handle agent-pool-mode workspaces.

**Workaround:** Created workspace via raw API with explicit `agent-pool-id` and
`execution-mode: agent` in the payload.

**Ideal outcome:** `terrapyne workspace clone` should copy the execution mode
and agent pool from the source workspace. Or `terrapyne workspace create` should
accept `--execution-mode agent --agent-pool-id <id>`.

---

## F7: No way to unlock a workspace

**Context:** Workspace was locked by a cancelled/errored run. Needed to unlock
before the next run could proceed.

**Workaround:** `curl -X POST .../workspaces/{id}/actions/unlock`.

**Ideal outcome:** `terrapyne workspace unlock` (and `terrapyne workspace lock`
for completeness).

---

## F8: `run apply` doesn't accept `--auto-apply` flag

**Context:** Tried `terrapyne run apply <id> --auto-apply` and got
"No such option: --auto-apply".

**Workaround:** Used `run apply` then `run watch --auto-apply` separately.

**Ideal outcome:** Either document that `--auto-apply` is only on `run watch`,
or add it to `run apply` so it applies and then watches in one command.

---

## Summary of API fallbacks used

| Operation | terrapyne gap | API used |
|-----------|--------------|----------|
| Cancel pending run | No `cancel` command | `POST /runs/{id}/actions/cancel` |
| Unlock workspace | No `unlock` command | `POST /workspaces/{id}/actions/unlock` |
| Create workspace with agent pool | Clone fails with 422 | `POST /organizations/{org}/workspaces` |
| Rename workspace | No rename command | `PATCH /workspaces/{id}` |
| Set workspace working-directory | No command | `PATCH /workspaces/{id}` |
| Set workspace variable | No command from CLI | `POST /workspaces/{id}/vars` |
| Trigger run by workspace ID | Auto-detect fails after rename | `POST /runs` with workspace relationship |
