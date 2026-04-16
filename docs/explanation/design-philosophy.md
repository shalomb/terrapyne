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
