# Security Policy

## Supported Versions

Currently, only the latest minor version of Terrapyne is actively supported with security updates. 

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |

*Note: Since the project is in early stages (0.x.x), we highly recommend staying on the absolute latest release.*

## Reporting a Vulnerability

Security is a top priority for Terrapyne, especially since this tool interacts directly with infrastructure management APIs and handles sensitive Terraform Cloud tokens.

If you discover a vulnerability, **do not open a public issue.**

Please report security issues responsibly by sending an email to the project maintainers or using GitHub's private vulnerability reporting feature if enabled on this repository. 

Please include the following information in your report:
- The version of Terrapyne you are using.
- The operating system and Python version.
- Detailed steps to reproduce the vulnerability.
- A brief description of the potential impact.

### What to expect

1. We will acknowledge receipt of your report within 48 hours.
2. We will investigate the issue and determine if it is a valid vulnerability.
3. We will keep you updated on our progress as we develop a fix.
4. Once a fix is ready, we will publish a new release and credit you (if desired) for the discovery.

### Safe Handling of Tokens
By design, Terrapyne looks for Terraform Cloud tokens in `~/.terraform.d/credentials.tfrc.json` or the `TFE_TOKEN` environment variable. If you find a scenario where Terrapyne inadvertently logs, leaks, or exposes these credentials (e.g., in debug logs or stdout/stderr outputs), please report it immediately using the process above.
