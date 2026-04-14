# terrapyne Documentation

> **📖 Purpose**: Central navigation for users and agents working with terrapyne.
> Organized by use case and learning style (Diataxis framework).

## 🎯 Quick Start by Role

| Role | Start Here | Focus |
|------|-----------|-------|
| **New User** | [Getting Started](#tutorials) | Learn to use the CLI |
| **Developer** | [Architecture](architecture/) | Understand the codebase |
| **Operator** | [How-to Guides](#how-to-guides) | Common tasks and troubleshooting |
| **Architect** | [Platform Integration](reference/platform-dependency-mapping.md) | Ecosystem fit and dependencies |

---

## 📚 Documentation Structure (Diataxis)

### 📖 Tutorials (Learning-oriented)
**Learn by doing** — step-by-step guides for common workflows

- **[Workspace Management Tutorial](tutorials/workspace-management.md)** *(planned)* — Create, list, show, and configure workspaces
- **[Run Execution Tutorial](tutorials/run-execution.md)** *(planned)* — Trigger, monitor, and debug runs

### 🛠️ How-to Guides (Problem-oriented)
**Accomplish a goal** — recipes for specific tasks

#### **Workspace Operations**
- **[List workspaces by project](how-to-guides/list-workspaces-by-project.md)** *(planned)* — Filter and organize workspaces
- **[Create workspace variables in bulk](how-to-guides/bulk-variable-creation.md)** *(planned)* — Automate variable injection

#### **Run Management**
- **[Stream and monitor run logs](how-to-guides/monitor-run-logs.md)** *(planned)* — Follow real-time plan/apply output
- **[Troubleshoot failed runs](how-to-guides/troubleshoot-runs.md)** *(planned)* — Diagnose and fix run issues

#### **State & Configuration**
- **[Export and analyze state](how-to-guides/export-and-analyze-state.md)** *(planned)* — Download state versions, compare outputs
- **[Clone workspace configuration](how-to-guides/clone-workspaces.md)** *(planned)* — Duplicate workspace state and variables

#### **VCS Integration**
- **[Manage VCS branches](how-to-guides/manage-vcs-branches.md)** — Update workspace source control settings

### 📖 Reference (Information-oriented)
**How things work** — specs, APIs, and technical details

#### **Architecture**
- **[System Context (C4-L1)](architecture/c4-l1-system-context.md)** — terrapyne + TFC + terraform binary + external systems
- **[Containers (C4-L2)](architecture/c4-l2-containers.md)** — CLI vs SDK boundary, data flows
- **[Components (C4-L3)](architecture/c4-l3-components.md)** — API classes, models, utilities, context resolution
- **[Architecture Decision Records](architecture/)** — Design decisions (ADR-001 through ADR-004)

#### **Integration & Dependencies**
- **[Platform Dependency Mapping](reference/platform-dependency-mapping.md)** — External systems, integration points, risks
- **[Takeda Ecosystem Integration](reference/takeda-ecosystem.md)** *(planned)* — AVM, TEC, LeanIX patterns

#### **API Reference**
- **[CLI Command Reference](reference/cli-reference.md)** *(planned)* — All commands, flags, examples
- **[SDK Reference](reference/sdk-reference.md)** *(planned)* — Python API, models, exceptions

#### **Data Formats**
- **[Terraform State Format](reference/terraform-state-format.md)** *(planned)* — State structure, outputs, remote config
- **[TFC JSON:API Format](reference/tfc-json-api.md)** *(planned)* — Request/response structure, pagination

### 💡 Explanation (Understanding-oriented)
**Why things are the way they are** — conceptual backgrounds

- **[Design Philosophy](explanation/design-philosophy.md)** *(planned)* — Why we built terrapyne this way
- **[TFC Workspace Model](explanation/tfc-workspace-model.md)** *(planned)* — How TFC organizes workspaces and runs
- **[Local Context Resolution](explanation/local-context-resolution.md)** *(planned)* — How terrapyne discovers your organization and workspace

---

## 🗂️ Directory Structure

```
docs/
├── README.md                          (You are here)
├── architecture/                      (C4 diagrams + ADRs)
│   ├── README.md
│   ├── c4-l1-system-context.md
│   ├── c4-l2-containers.md
│   ├── c4-l3-components.md
│   └── ADR-*.md
├── reference/                         (Technical specs, dependencies)
│   ├── platform-dependency-mapping.md
│   └── (cli-reference, sdk-reference, etc. — planned)
├── how-to-guides/                     (Task-oriented recipes — planned)
├── tutorials/                         (Learning-oriented walkthroughs — planned)
└── explanation/                       (Conceptual backgrounds — planned)
```

---

## 🔗 External Resources

- **[Terraform Cloud Documentation](https://developer.hashicorp.com/terraform/cloud-docs)**
- **[Terraform Cloud API Reference](https://developer.hashicorp.com/terraform/cloud-docs/api-docs)**
- **[GitHub: terrapyne Repository](https://github.com/shalomb/terrapyne)**

---

## 📝 Contributing to Docs

When adding new documentation:

1. **Choose the right category**: Is this a tutorial, how-to, reference, or explanation?
2. **Follow Diataxis structure**: See existing files for style and organization
3. **Keep it concise**: Readers skim; make the goal clear in the first paragraph
4. **Link to related docs**: Help readers find connected topics
5. **Update this README**: Add your file to the appropriate section

---

## 📅 Maintenance

| Section | Maintainer | Last Updated | Next Review |
|---------|-----------|--------------|-------------|
| Architecture | Maintainers | 2026-04-14 | 2026-07-14 |
| API Reference | Maintainers | — (planned) | — |
| Integration Guide | Platform Team | — (planned) | — |

---

**Status**: MVP documentation complete; tutorials and how-to guides to follow
