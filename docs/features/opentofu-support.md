# Feature Design: OpenTofu Support

## Overview
`terrapyne` is primarily a Python SDK and CLI for Terraform Cloud (TFC). However, it also includes a local execution wrapper (`terrapyne.local`) to run Terraform commands locally. 

This document outlines the design and constraints for officially supporting OpenTofu within the `terrapyne.local` wrapper.

## The Existential Conflict: OpenTofu vs Terraform Cloud
HashiCorp explicitly restricts OpenTofu from natively using Terraform Cloud as a backend. Therefore, **OpenTofu and Terraform Cloud are fundamentally incompatible**.

This creates a split in `terrapyne`'s functionality when encountering an OpenTofu project:
1. **SDK Usage:** Developers can use `terrapyne.local.OpenTofu` strictly for local execution, which is highly valuable. If they attempt to pass OpenTofu state into the TFC API modules (`terrapyne.api`), the API will natively return HTTP errors.
2. **CLI Usage (`tfc`):** The `tfc` CLI is deeply opinionated around Terraform Cloud. If the CLI detects an OpenTofu project, it MUST intercept and block TFC API commands (e.g., `tfc run create`) with a clear error: *"Terraform Cloud API operations are not supported for OpenTofu projects."* 

In the future, we will introduce a `tfc local` command group for agnostic local operations (e.g., `tfc local plan parse`).

## Heuristic Auto-Detection
To provide a seamless yet safe developer experience, `terrapyne` will use **Heuristic Auto-Detection** to determine the correct underlying binary (`terraform` vs `tofu`). Guessing based solely on what is installed in `$PATH` is highly dangerous and can lead to state corruption. 

Before execution, `terrapyne` will perform sub-millisecond inspections of local project files to find "hallmarks" of the target runner.

### Hallmarks
1. **The Lockfile (`.terraform.lock.hcl`):**
   - **Terraform:** Contains `# This file is maintained automatically by "terraform init".` and uses `registry.terraform.io`.
   - **OpenTofu:** Contains `# This file is maintained automatically by "tofu init".` and uses `registry.opentofu.org`.
2. **Version Manager Files:**
   - `.opentofu-version` strictly guarantees OpenTofu.
   - `.terraform-version` strongly implies Terraform.

## Workflow Analysis & Safety Rules

Based on the heuristics above, `terrapyne` enforces strict safety boundaries across different developer workflows:

### 1. Existing, Initialized Project
- **Context:** The directory contains `.terraform.lock.hcl`.
- **Behavior:** Parse the lockfile to determine the runner.
- **Safety Rule:** If OpenTofu is detected but the `tofu` binary is missing from `$PATH`, `terrapyne` **MUST FAIL** with a clear error. It must NEVER silently fall back to `terraform` (and vice-versa).

### 2. Freshly Cloned Project (Uninitialized)
- **Context:** No `.terraform/` directory, but `.terraform.lock.hcl` or version manager files are committed to source control.
- **Behavior:** Inspect the committed lockfile and version manager files to auto-detect the correct runner.

### 3. Brand New Project
- **Context:** Empty directory or just `.tf` files. No state, no lockfile.
- **Behavior:** Auto-detection is impossible. 
- **Safety Rule:** `terrapyne` must require an explicit configuration (e.g., `TERRAPYNE_RUNNER=tofu`) or prompt the user. It must not guess.

### 4. The "Migration" Workflow
- **Context:** A team is intentionally migrating a project from Terraform to OpenTofu.
- **Behavior:** The user must explicitly pass a bypass flag (e.g., `--force-runner tofu` in the CLI or `force_runner=True` in the SDK) to override the heuristic detection and allow `tofu` to initialize over an existing `terraform` lockfile/state.

## Implementation Details
- Rename `terrapyne.local.Terraform` core logic to a base `LocalIACRunner` class.
- Create explicit `Terraform(LocalIACRunner)` and `OpenTofu(LocalIACRunner)` subclasses.
- Implement a `detect_runner(directory)` factory function that executes the fast heuristic checks and returns the appropriate subclass instance.
