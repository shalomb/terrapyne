# Explanation & Understanding

Explanation-oriented documentation provides conceptual background and context. It answers the question **"Why?"** and helps you understand the design philosophy and internal mechanics of Terrapyne.

## 🏛️ Architecture & Design

- **[Architecture & ADRs](architecture/)** — The blueprint of Terrapyne, including C4 diagrams and Architecture Decision Records (ADRs).
- **[Design Philosophy](design-philosophy.md)** *(planned)* — Why we built Terrapyne as a CLI/SDK hybrid.

## ⚙️ Core Mechanics

- **[BDD Specifications](bdd-specifications.md)** — Deep dive into our behavior-driven development process and how it ensures software quality.
- **[Plan Parser Analysis](plan-parser.md)** — Technical details on how Terrapyne extracts structured data from the unstructured text output of Terraform plans.
- **[TFC Workspace Model](tfc-workspace-model.md)** *(planned)* — How Terrapyne maps to the Terraform Cloud conceptual model.
- **[Local Context Resolution](local-context-resolution.md)** *(planned)* — How the CLI automatically discovers your organization and workspace from local state.

## 💡 Key Concepts

- **Type-Safety with Pydantic**: How we use Pydantic to enforce data integrity across the SDK.
- **Unix Philosophy in CLI**: Why every command supports JSON and how to pipe them effectively.
