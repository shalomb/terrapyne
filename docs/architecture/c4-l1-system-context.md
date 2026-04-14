# C4 Level 1: System Context

**terrapyne in relation to the external world**

## Overview

Terrapyne is a Python CLI and SDK for managing Terraform Cloud workspaces, runs, projects, teams, and state versions. This diagram shows terrapyne as a system and the key external actors and systems it interacts with.

## System Context Diagram

```mermaid
graph TB
    User["👤 DevOps Engineer<br/>(End User)"]
    TFC["Terraform Cloud<br/>(REST API)"]
    TFE["Terraform Enterprise<br/>(REST API)"]
    TF["terraform binary<br/>(Subprocess)"]
    S3["AWS S3<br/>(Signed URLs)"]
    Browser["OS Web Browser<br/>(Opens URLs)"]
    VCS["VCS Providers<br/>(GitHub, GitLab, etc.)"]
    
    Terrapyne["🐍 terrapyne<br/>(CLI + SDK)"]
    
    User -->|"runs terrapyne CLI<br/>or imports SDK"| Terrapyne
    
    Terrapyne -->|"HTTP + Bearer Token<br/>(JSON:API)"| TFC
    Terrapyne -->|"HTTP + Bearer Token<br/>(JSON:API)"| TFE
    
    Terrapyne -->|"Subprocess:<br/>terraform login<br/>terraform apply"| TF
    TF -->|"Reads/writes state"| TFC
    
    Terrapyne -->|"Generates signed URLs<br/>for direct download"| S3
    
    Terrapyne -->|"Instructs user to<br/>open URLs in browser<br/>for auth flows"| Browser
    Browser -->|"OAuth handshake"| TFC
    Browser -->|"OAuth handshake"| VCS
    
    TFC -.->|"Connects workspaces<br/>to repositories"| VCS
    
    style User fill:#e1f5ff
    style Terrapyne fill:#fff3e0
    style TFC fill:#f3e5f5
    style TFE fill:#f3e5f5
    style TF fill:#e8f5e9
    style S3 fill:#fce4ec
    style Browser fill:#e0f2f1
    style VCS fill:#f1f8e9
```

## Key Interactions

| Actor/System | How terrapyne uses it | Authentication |
|---|---|---|
| **Terraform Cloud / Enterprise** | Queries workspace state, triggers runs, manages teams and projects | Bearer token in `Authorization` header |
| **terraform binary** | Parses plans, validates syntax, executes `terraform login` for OAuth | Subprocess invocation |
| **AWS S3** | Generates signed URLs for users to download state exports | TFC API provides pre-signed URLs |
| **Web Browser** | Opens for VCS OAuth authorization flows | User-initiated via `typer.confirm()` → `webbrowser.open()` |
| **VCS Providers** | Connected through TFC; terrapyne does not contact directly | TFC manages OAuth tokens |

## Design Notes

- **No direct VCS access**: Terrapyne uses TFC as the VCS gateway. VCS credentials and OAuth tokens are managed by TFC.
- **CLI + SDK split**: The CLI is a consumer of the SDK; both expose the same underlying `TFCClient` and API classes.
- **Local context resolution**: Terrapyne resolves organization and workspace names from environment variables or local Terraform configuration files (`.terraform/terraform.tfstate`, `terraform.tf`) before calling TFC.
- **Subprocess minimization**: The `terraform` binary is used sparingly—mainly for `terraform login` OAuth flows and plan parsing. Most operations use the TFC API directly.
