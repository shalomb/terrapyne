# terrapyne Documentation

> **📖 Purpose**: Central navigation for users and agents working with terrapyne.
> Organized by use case and learning style (Diataxis framework).

## 🎯 Quick Start by Role

| Role | Start Here | Focus |
|------|-----------|-------|
| **New User** | [Tutorials](tutorials/) | Learn to use the CLI |
| **Developer** | [How-to Guides](how-to/) | Development workflows |
| **Architect** | [Architecture](explanation/architecture/) | System design and ADRs |
| **Operator** | [Reference](reference/) | Specs and dependencies |

---

## 📚 Documentation Structure (Diataxis)

### 📖 [Tutorials](tutorials/) (Learning-oriented)
**Learn by doing** — step-by-step guides for common workflows.

- **[Workspace Management Tutorial](tutorials/workspace-management.md)** *(planned)* — Create, list, show, and configure workspaces.
- **[Run Execution Tutorial](tutorials/run-execution.md)** *(planned)* — Trigger, monitor, and debug runs.

### 🛠️ [How-to Guides](how-to/) (Problem-oriented)
**Accomplish a goal** — recipes for development and operational tasks.

#### **Development**
- **[Python & Testing](how-to/python-and-testing.md)** — Type hints, imports, test structure, and pytest-bdd.
- **[Commits & Review](how-to/commits-and-review.md)** — Atomic commits, conventional formats, and PR workflow.

#### **Workspace Operations**
- **[List workspaces by project](how-to/list-workspaces-by-project.md)** — Filter and organize workspaces.
- **[Create workspace variables in bulk](how-to/bulk-variable-creation.md)** *(planned)* — Automate variable injection.

### 💡 [Explanation](explanation/) (Understanding-oriented)
**Why things are the way they are** — conceptual backgrounds and design.

- **[Architecture & ADRs](explanation/architecture/)** — System context, container diagrams, and decision records.
- **[Design Philosophy](explanation/design-philosophy.md)** — Why we built Terrapyne as a CLI/SDK hybrid.
- **[BDD Specifications](explanation/bdd-specifications.md)** — Understanding our behavior-driven development approach.
- **[Plan Parser Analysis](explanation/plan-parser.md)** — How we extract data from plain text plans.

### 📖 [Reference](reference/) (Information-oriented)
**How things work** — specs, APIs, and technical details.

- **[SDK Reference](reference/sdk.md)** — Python library documentation and examples.
- **[CLI Command Reference](reference/cli-reference.md)** — All commands, flags, and examples.
- **[Platform Dependency Mapping](reference/platform-dependency-mapping.md)** — External systems, integration points, and risks.

---

## 🗂️ Project Documentation Map

```
docs/
├── explanation/       (Concepts, Architecture, Design)
│   └── architecture/  (ADRs, C4 Diagrams)
├── how-to/            (Dev workflows, operational recipes)
├── reference/         (Specs, API docs, dependency maps)
├── tutorials/         (Step-by-step walkthroughs)
└── README.md          (Navigation hub)
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
