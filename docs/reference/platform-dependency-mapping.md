# Platform Dependency Mapping

## Executive Summary

This document maps the dependencies and integration points between terrapyne and the Terraform Cloud ecosystem, along with the broader infrastructure platform. Understanding these dependencies is crucial for ensuring seamless integration, avoiding conflicts, and planning compatibility with AVM/Internal Platform standards.

## Dependency Matrix

### 1. **Terraform Cloud Dependencies**

#### **Terraform Cloud API**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **TFC REST API** | External API | Workspace, run, project, team, state management | Critical | ✅ Implemented |
| **TFC Authentication** | Authentication | Bearer token auth, OAuth flows | Critical | ✅ Implemented |
| **JSON:API Format** | Data Format | Request/response serialization, includes parameter | Critical | ✅ Implemented |
| **Pagination** | Data Pattern | Cursor-based pagination for large result sets | High | ✅ Implemented |
| **Run Streaming** | Data Stream | Plan/apply log polling and streaming | Medium | ✅ Implemented |
| **Rate Limiting** | Service Limit | API quota management (per org/user) | Medium | ⏳ Planned (Phase 2) |
| **Webhooks** | Event Stream | Workspace/run change notifications (future) | Low | ⏳ Pending |

#### **Terraform Enterprise (TFE)**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **TFE API Compatibility** | Compatibility | API parity with TFC | High | ⏳ Planned |
| **TFE Authentication** | Authentication | Self-hosted token patterns | High | ⏳ Pending |
| **Custom Domain Support** | Network | Non-app.terraform.io endpoints | Medium | ⏳ Pending |

#### **VCS Integration** (GitHub, GitLab, Bitbucket)
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **OAuth Token Management** | Authentication | TFC-managed VCS OAuth tokens | High | ✅ Implemented |
| **Repository Metadata** | Data Structure | VCS identifier, branch, working directory | High | ✅ Implemented |
| **Branch Updates** | Mutation | Change workspace source branch | Medium | ✅ Implemented |
| **Direct VCS Access** | External API | (Not used; TFC acts as gateway) | Low | ⏳ Planned |

### 2. **Local Terraform Ecosystem**

#### **Terraform Binary**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **terraform show -json** | Subprocess | Parse plan/apply output | Medium | ✅ Implemented |
| **terraform login** | Subprocess | OAuth token management (user-initiated) | Medium | ✅ Implemented |
| **terraform init** | Subprocess | (Not used by terrapyne; user domain) | Low | — |
| **terraform apply** | Subprocess | (Not used; TFC handles execution) | Low | — |

#### **Local Configuration Files**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **~/.tfc/credentials** | Local File | API token storage (TFC format) | High | ✅ Implemented |
| **.terraform/terraform.tfstate** | Local File | Workspace context resolution | High | ✅ Implemented |
| **terraform.tf** | Local File | Cloud block parsing for backend context | Medium | ✅ Implemented |
| **.terraform.lock.hcl** | Local File | (Not used by terrapyne) | Low | — |

#### **Local Terraform State**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **State Version Snapshots** | Data Download | Retrieve and compare state versions | Medium | ✅ Implemented |
| **State Outputs** | Data Extract | List outputs from state versions | Medium | ✅ Implemented |
| **S3 Signed URLs** | External URL | Download state exports | Medium | ✅ Implemented |

### 3. **Infrastructure Platform (Internal)**

#### **AVM (Automated Vending Machine)**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **AVM Foundational Resources** | Resource Pattern | Identify AVM-managed base infrastructure | High | ⏳ Planned (Phase 2) |
| **AVM Resource Tagging** | Data Pattern | Filter by AVM ownership tags | High | ⏳ Planned (Phase 2) |
| **AVM Building Blocks** | Module Library | Reference implementations for IaC patterns | High | ⏳ Planned (Phase 3) |

#### **Internal Platform AWS Accounts**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **Cross-Account Role Patterns** | Authentication | TFC workspace IAM role assumption | High | ⏳ Planned |
| **Resource Tagging Standards** | Data Pattern | APMS-ID, cost center, environment tags | High | ⏳ Planned |
| **Network Architecture** | Infrastructure | VPC, subnet, security group discovery | Medium | ⏳ Planned |

#### **Internal Platform Service Integration**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **TFC Workspace Standards** | Convention | Naming, tagging, team assignment patterns | Medium | ⏳ Planned |
| **State Management Strategy** | Strategy | Remote state consolidation, organization | Medium | ⏳ Planned |

### 4. **External Internal Systems**

#### **LeanIX Integration**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **APMS Data** | External API | Application metadata, business unit mapping | Medium | ⏳ Pending |
| **Application Names** | Data Structure | Map TFC workspace names to applications | Medium | ⏳ Pending |
| **Business Unit Mapping** | Data Structure | Workspace to cost center/org unit mapping | Medium | ⏳ Pending |

#### **ServiceNow/CMDB**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **CI (Configuration Item) Data** | External API | Track Terraform-managed infrastructure | Medium | ⏳ Pending |
| **Change Management** | Workflow | Request/approval integration | Low | ⏳ Pending |

#### **GitHub Enterprise**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **Repository Enumeration** | Metadata | List VCS-connected repositories | Medium | ✅ Implemented (via TFC VCS API) |
| **Team Management** | Authorization | Sync TFC teams with GitHub org teams | Medium | ⏳ Planned |

### 5. **Development & Testing**

#### **pytest & BDD Framework**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **pytest** | Test Framework | Unit and integration testing | High | ✅ Implemented |
| **pytest-bdd** | BDD Framework | Gherkin feature specifications | High | ✅ Implemented |
| **Fixtures & Mocks** | Test Pattern | Mock TFCClient for isolated testing | High | ✅ Implemented |

#### **Type Checking & Linting**
| Dependency | Type | Purpose | Impact | Status |
|------------|------|---------|--------|--------|
| **mypy** | Type Checker | Python type annotations validation | Medium | ✅ Implemented |
| **ruff** | Linter/Formatter | Code style, import organization | Medium | ✅ Implemented |

---

## Integration Points

### 1. **Critical Integration Points**

#### **TFC API Workspace Discovery**
- **Purpose**: Query workspaces within an organization, resolve workspace context
- **API Endpoints**: `GET /v2/organizations/{org}/workspaces`, `GET /v2/workspaces/{id}`
- **Dependencies**: Bearer token, organization name, workspace naming patterns
- **Impact**: Core to every CLI command that requires workspace context
- **Risk**: TFC API unavailability blocks all operations
- **Status**: ✅ Implemented
- **Priority**: Critical

#### **Run Lifecycle Management**
- **Purpose**: List, show, create, cancel, and stream logs for runs
- **API Endpoints**: `GET /v2/runs`, `GET /v2/runs/{id}`, `POST /v2/runs`, `GET /v2/runs/{id}/logs/{stage}`
- **Dependencies**: Workspace ID, plan/apply log access, run status polling
- **Impact**: Central to `tfc run` command family
- **Risk**: Log streaming timeout, incomplete plan/apply downloads
- **Status**: ✅ Implemented
- **Priority**: Critical

#### **Local Context Resolution**
- **Purpose**: Auto-discover organization/workspace from local Terraform files
- **Sources**: `TFC_ORG` env var, `TFC_WORKSPACE` env var, `.terraform/terraform.tfstate`, `terraform.tf`
- **Dependencies**: File system access, JSON parsing
- **Impact**: Reduces CLI flag verbosity for frequent operations
- **Risk**: Incorrect context resolution if files are stale or misconfigured
- **Status**: ✅ Implemented
- **Priority**: High

#### **VCS Branch Management**
- **Purpose**: Update workspace VCS branch, list connected repositories
- **API Endpoints**: `PATCH /v2/workspaces/{id}`, `GET /v2/vcs-repos`
- **Dependencies**: OAuth token ID, VCS identifier, branch name
- **Impact**: Enable workspace source control workflow automation
- **Risk**: OAuth token expiry, invalid branch names
- **Status**: ✅ Implemented
- **Priority**: High

### 2. **Supporting Integration Points**

#### **Project Management**
- **Purpose**: Query projects, list project-assigned workspaces, workspace counts
- **API Endpoints**: `GET /v2/projects`, `GET /v2/projects/{id}`, `POST /v2/projects`
- **Dependencies**: Organization-to-project mapping
- **Impact**: Support project-scoped workspace discovery and organization
- **Risk**: Project ID consistency, project-to-workspace hierarchy changes
- **Status**: ✅ Implemented
- **Priority**: Medium

#### **Team Management**
- **Purpose**: List teams, manage team members and workspace access
- **API Endpoints**: `GET /v2/teams`, `POST /v2/team-members`, `GET /v2/team-project-access`
- **Dependencies**: Team names, user invitations, role mappings
- **Impact**: Support team-based access control for workspaces
- **Risk**: Permission boundaries, role definition changes
- **Status**: ✅ Implemented (basic); ⏳ Planned (advanced)
- **Priority**: Medium

#### **State Version Management**
- **Purpose**: Download, compare, and analyze state versions
- **API Endpoints**: `GET /v2/state-versions`, `GET /v2/state-versions/{id}/outputs`, `GET /v2/state-versions/{id}/json-download`
- **Dependencies**: State version ID, S3 signed URL handling
- **Impact**: Enable state analysis, drift detection, disaster recovery
- **Risk**: Large state file downloads, S3 URL expiry
- **Status**: ✅ Implemented (basic)
- **Priority**: Medium

#### **Workspace Variables**
- **Purpose**: List, create, update, delete workspace variables (Terraform and environment)
- **API Endpoints**: `GET /v2/workspaces/{id}/vars`, `POST /v2/workspaces/{id}/vars`, `PATCH /v2/vars/{id}`, `DELETE /v2/vars/{id}`
- **Dependencies**: Variable name/value, HCL escaping, sensitive flag handling
- **Impact**: Automate variable injection, environment configuration
- **Risk**: Sensitive value exposure, variable naming conflicts
- **Status**: ✅ Implemented
- **Priority**: Medium

### 3. **Future Integration Points** (Phase 2+)

#### **Cost Management & Budget Tracking**
- **Purpose**: Query workspace costs, resource pricing
- **API Endpoints**: `GET /v2/workspaces/{id}/costs` (if available)
- **Dependencies**: Cost allocation metadata, resource tagging
- **Impact**: Enable cost-aware workspace decisions
- **Status**: ⏳ Pending API availability
- **Priority**: Low

#### **Compliance & Audit Logging**
- **Purpose**: Track configuration changes, audit workspace modifications
- **API Endpoints**: Audit log endpoints (if available in TFC)
- **Dependencies**: Change tracking, compliance reporting requirements
- **Impact**: Support compliance workflows
- **Status**: ⏳ Pending API availability
- **Priority**: Low

#### **Workspace Cloning at Scale**
- **Purpose**: Clone workspace state, variables, and VCS configuration across multiple workspaces
- **Dependencies**: `CloneWorkspaceAPI`, batch operation patterns
- **Impact**: Enable disaster recovery, environment promotion
- **Status**: ✅ Implemented (single clone); ⏳ Planned (batch)
- **Priority**: Medium

---

## Risk Assessment

### 1. **High-Risk Dependencies**

#### **TFC API Availability**
- **Risk**: API downtime blocks all terrapyne operations
- **Mitigation**:
  - Cache workspace metadata locally (configurable TTL)
  - Implement offline mode for read-only operations
  - Add circuit breaker for cascading failures
- **Status**: ⚠️ Partial mitigation (caching); ⏳ Planned (offline mode)
- **Owner**: SDK layer (TFCClient)

#### **Exponential Backoff for Log Streaming**
- **Risk**: Log polling with insufficient backoff causes rate limiting
- **Mitigation**:
  - Exponential backoff up to max interval (default: 30s)
  - User-configurable polling intervals
  - Graceful handling of incomplete logs
- **Status**: ✅ Implemented
- **Owner**: CLI layer (run follow command)

#### **VCS OAuth Token Expiry**
- **Risk**: OAuth tokens expire, blocking VCS operations
- **Mitigation**:
  - Store token ID (not token value) in configuration
  - Prompt user to re-authorize via TFC UI
  - Document token refresh workflow
- **Status**: ✅ Implemented (token storage); ⏳ Planned (auto-refresh)
- **Owner**: VCS API layer

#### **Large State File Downloads**
- **Risk**: S3 signed URLs expire, state downloads timeout
- **Mitigation**:
  - Validate URL freshness before download
  - Implement resumable downloads for large files
  - Fall back to streaming if full download fails
- **Status**: ⏳ Planned (Phase 2)
- **Owner**: StateVersionsAPI

### 2. **Medium-Risk Dependencies**

#### **Local File Context Staleness**
- **Risk**: `.terraform/terraform.tfstate` becomes stale; auto-context resolves incorrectly
- **Mitigation**:
  - Warn user if state file is older than 24 hours
  - Provide `--force-org` flag to override local detection
  - Validate resolved context against TFC before operations
- **Status**: ✅ Partial (basic detection); ⏳ Planned (staleness warnings)
- **Owner**: Context resolution layer

#### **Rate Limiting (TFC/AWS)**
- **Risk**: TFC API rate limits impact discovery performance
- **Mitigation**:
  - Implement request queuing with token bucket algorithm
  - Cache paginated results to reduce redundant calls
  - Expose rate limit headers to user
- **Status**: ⏳ Planned (Phase 2)
- **Owner**: TFCClient retry logic

#### **Cross-Account IAM Role Assumption**
- **Risk**: TFC workspace lacks permissions for cross-account resource access
- **Mitigation**:
  - Document TerraformIaC role requirements
  - Validate IAM permissions before running sensitive operations
  - Provide role assumption error messages with remediation steps
- **Status**: ⏳ Planned (Phase 2)
- **Owner**: AWS integration layer

### 3. **Low-Risk Dependencies**

#### **Terraform Binary Path Resolution**
- **Risk**: `terraform` binary not in PATH, subprocess calls fail
- **Mitigation**:
  - Graceful error message with `which terraform` suggestion
  - Allow user to specify custom terraform path via env var
  - Cache terraform version on first invocation
- **Status**: ✅ Implemented (basic); ⏳ Planned (caching)
- **Owner**: Terraform class

#### **JSON Serialization of Custom Types**
- **Risk**: Non-standard types (datetime, Pydantic models) fail JSON export
- **Mitigation**:
  - Custom JSON encoder in `emit_json()` utility
  - Explicit handling for datetime, model_dump(), __dict__
- **Status**: ✅ Implemented
- **Owner**: CLI utils layer

---

## Compatibility & Standards

### **Internal Standards** (Planned Integration)

| Standard | Relevance | Status | Notes |
|----------|-----------|--------|-------|
| **AVM Foundational Resources** | Filter excluded resources during discovery | ⏳ Phase 2 | Requires AVM resource tagging standards |
| **Resource Tagging** | APMS-ID, cost center, environment tagging | ⏳ Phase 2 | Align with Internal Platform tagging policies |
| **Building Block Patterns** | Terraform module composition, versions | ⏳ Phase 3 | Reference AVM building blocks for code generation |
| **Cross-Account Architecture** | Multi-account workspace organization | ⏳ Phase 2 | Support Internal Platform cross-account patterns |

### **Terraform Best Practices**

| Practice | Implementation | Status |
|----------|----------------|--------|
| **State Locking** | Via TFC (default) | ✅ Implemented |
| **Remote State** | Via TFC workspace runs | ✅ Implemented |
| **Version Pinning** | Module source ~> syntax | ✅ Supported in generated code |
| **Variable Validation** | Via Pydantic models | ✅ Implemented |

---

## Dependency Graph

```
terrapyne
├── TFC API
│   ├── Workspaces (list, show, create, update)
│   ├── Runs (list, show, stream logs)
│   ├── Projects (list, show)
│   ├── Teams (list, manage)
│   ├── State Versions (download, compare)
│   └── VCS Integration (update branch, list repos)
├── Local Context
│   ├── ~/.tfc/credentials
│   ├── .terraform/terraform.tfstate
│   └── terraform.tf
├── Terraform Binary
│   ├── show -json (plan/apply parsing)
│   └── login (OAuth flow)
├── Internal Platform (Future)
│   ├── AVM (resource filtering)
│   ├── Internal Platform (account/network context)
│   └── LeanIX (application metadata)
└── External Systems (Future)
    ├── GitHub (repository enumeration)
    ├── ServiceNow (change management)
    └── S3 (state exports)
```

---

## Decision: Out-of-Scope for MVP

The following integrations are **deferred beyond MVP** due to complexity, external API availability, or lower priority:

| Integration | Reason | Timeline |
|-------------|--------|----------|
| **AVM Resource Discovery** | Requires AVM tagging standards finalization | Phase 2 |
| **LeanIX APMS Integration** | External API dependency, low user feedback | Future |
| **ServiceNow Change Tickets** | Workflow complexity, governance overhead | Future |
| **Webhook-based Run Notifications** | Event-driven architecture complexity | Future |
| **Cost Analytics** | TFC cost API availability unclear | Future |
| **Multi-tenancy** | Organization switching complexity | Future |
| **Batch Workspace Cloning** | Scope creep; single-clone MVP sufficient | Phase 2 |

---

## Review & Update Cadence

This document should be reviewed quarterly or when:
- Major API breaking changes occur in TFC
- New integrations are planned
- Risk assessments reveal new dependencies
- AVM/Internal Platform standards are finalized

**Last Updated**: 2026-04-14  
**Next Review**: 2026-07-14  
**Owner**: terrapyne maintainers
