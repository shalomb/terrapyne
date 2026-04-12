"""Fixtures for mocking TFC API responses.

This module provides pytest fixtures that return realistic TFC API responses
for use in BDD and unit tests.
"""

import pytest


@pytest.fixture
def workspace_list_response():
    """Mock response for listing workspaces."""
    return {
        "data": [
            {
                "id": "ws-1a2b3c4d5e6f7g8h",
                "type": "workspaces",
                "attributes": {
                    "name": "my-app-dev",
                    "created-at": "2025-03-13T07:50:15.781Z",
                    "terraform-version": "1.7.0",
                    "execution-mode": "remote",
                    "auto-apply": False,
                    "locked": False,
                    "tag-names": ["dev", "backend"],
                    "vcs-repo": {
                        "identifier": "myorg/my-app",
                        "branch": "develop",
                        "repository-http-url": "https://github.com/myorg/my-app",
                        "oauth-token-id": "ot-1a2b3c4d5e6f7g8h",
                    },
                },
                "relationships": {
                    "project": {
                        "data": {"id": "prj-abc123", "type": "projects"}
                    }
                },
            },
            {
                "id": "ws-2a3b4c5d6e7f8g9h",
                "type": "workspaces",
                "attributes": {
                    "name": "my-app-prod",
                    "created-at": "2025-03-14T08:30:20.123Z",
                    "terraform-version": "1.7.0",
                    "execution-mode": "remote",
                    "auto-apply": True,
                    "locked": False,
                    "tag-names": ["prod", "backend"],
                },
            },
        ],
        "meta": {"pagination": {"total-count": 2, "current-page": 1, "total-pages": 1}},
        "links": {
            "self": "https://app.terraform.io/api/v2/organizations/test-org/workspaces",
            "first": "https://app.terraform.io/api/v2/organizations/test-org/workspaces?page%5Bnumber%5D=1&page%5Bsize%5D=100",
            "last": "https://app.terraform.io/api/v2/organizations/test-org/workspaces?page%5Bnumber%5D=1&page%5Bsize%5D=100",
            "next": None,
        },
    }


@pytest.fixture
def workspace_detail_response():
    """Mock response for showing workspace details."""
    return {
        "data": {
            "id": "ws-1a2b3c4d5e6f7g8h",
            "type": "workspaces",
            "attributes": {
                "name": "my-app-dev",
                "created-at": "2025-03-13T07:50:15.781Z",
                "updated-at": "2025-03-15T10:20:30.456Z",
                "terraform-version": "1.7.0",
                "execution-mode": "remote",
                "auto-apply": False,
                "locked": False,
                "working-directory": "terraform/",
                "tag-names": ["dev", "backend"],
                "vcs-repo": {
                    "identifier": "myorg/my-app",
                    "branch": "develop",
                    "repository-http-url": "https://github.com/myorg/my-app",
                    "oauth-token-id": "ot-1a2b3c4d5e6f7g8h",
                    "working-directory": "terraform/",
                },
            },
            "relationships": {
                "project": {
                    "data": {"id": "prj-abc123", "type": "projects"}
                }
            },
        }
    }


@pytest.fixture
def workspace_variables_response():
    """Mock response for workspace variables."""
    return {
        "data": [
            {
                "id": "var-1a2b3c4d5e6f7g8h",
                "type": "vars",
                "attributes": {
                    "key": "region",
                    "value": "us-east-1",
                    "category": "terraform",
                    "sensitive": False,
                    "hcl": False,
                },
            },
            {
                "id": "var-2a3b4c5d6e7f8g9h",
                "type": "vars",
                "attributes": {
                    "key": "aws_access_key",
                    "value": "***",
                    "category": "env",
                    "sensitive": True,
                    "hcl": False,
                },
            },
        ],
        "meta": {"pagination": {"total-count": 2}},
    }


@pytest.fixture
def run_list_response():
    """Mock response for listing runs."""
    return {
        "data": [
            {
                "id": "run-abc123def456",
                "type": "runs",
                "attributes": {
                    "status": "applied",
                    "created-at": "2025-03-15T10:20:30.456Z",
                    "message": "Applied by user",
                    "auto-apply": False,
                    "is-destroy": False,
                    "refresh": True,
                    "resource-additions": 3,
                    "resource-changes": 2,
                    "resource-destructions": 0,
                },
                "relationships": {
                    "workspace": {
                        "data": {"id": "ws-1a2b3c4d5e6f7g8h", "type": "workspaces"}
                    }
                },
            },
            {
                "id": "run-def456ghi789",
                "type": "runs",
                "attributes": {
                    "status": "pending",
                    "created-at": "2025-03-16T11:30:40.789Z",
                    "message": None,
                    "auto-apply": False,
                    "is-destroy": False,
                    "refresh": True,
                    "resource-additions": 0,
                    "resource-changes": 1,
                    "resource-destructions": 0,
                },
            },
        ],
        "meta": {"pagination": {"total-count": 2}},
    }


@pytest.fixture
def run_detail_response():
    """Mock response for showing run details."""
    return {
        "data": {
            "id": "run-abc123def456",
            "type": "runs",
            "attributes": {
                "status": "applied",
                "created-at": "2025-03-15T10:20:30.456Z",
                "updated-at": "2025-03-15T10:25:50.123Z",
                "message": "Applied by user",
                "auto-apply": False,
                "is-destroy": False,
                "refresh": True,
                "refresh-only": False,
                "resource-additions": 3,
                "resource-changes": 2,
                "resource-destructions": 0,
                "target-addrs": [],
                "replace-addrs": [],
            },
            "relationships": {
                "workspace": {
                    "data": {"id": "ws-1a2b3c4d5e6f7g8h", "type": "workspaces"}
                }
            },
        }
    }


@pytest.fixture
def project_list_response():
    """Mock response for listing projects."""
    return {
        "data": [
            {
                "id": "prj-abc123",
                "type": "projects",
                "attributes": {
                    "name": "my-infrastructure",
                    "description": "Core infrastructure project",
                    "created-at": "2025-02-01T08:00:00.000Z",
                    "resource-count": 3,
                },
                "relationships": {
                    "organization": {
                        "data": {"id": "test-org", "type": "organizations"}
                    }
                },
            },
            {
                "id": "prj-def456",
                "type": "projects",
                "attributes": {
                    "name": "my-app-infrastructure",
                    "description": "Application infrastructure",
                    "created-at": "2025-02-15T09:30:00.000Z",
                    "resource-count": 2,
                },
            },
        ],
        "meta": {"pagination": {"total-count": 2}},
    }


@pytest.fixture
def project_detail_response():
    """Mock response for showing project details."""
    return {
        "data": {
            "id": "prj-abc123",
            "type": "projects",
            "attributes": {
                "name": "my-infrastructure",
                "description": "Core infrastructure project",
                "created-at": "2025-02-01T08:00:00.000Z",
                "resource-count": 3,
            },
            "relationships": {
                "organization": {
                    "data": {"id": "test-org", "type": "organizations"}
                }
            },
        }
    }


@pytest.fixture
def team_project_access_response():
    """Mock response for team project access."""
    return {
        "data": [
            {
                "id": "tprj-abc123",
                "type": "team-projects",
                "attributes": {
                    "access": "admin",
                    "project-access": {
                        "settings": "delete",
                        "teams": "manage",
                        "variable-sets": "write",
                    },
                    "workspace-access": {
                        "create": True,
                        "delete": True,
                        "move": True,
                        "locking": True,
                        "runs": "apply",
                        "variables": "write",
                        "state-versions": "write",
                        "run-tasks": True,
                    },
                },
                "relationships": {
                    "team": {
                        "data": {"id": "team-123", "type": "teams"},
                        "links": {
                            "related": "https://app.terraform.io/api/v2/teams/team-123"
                        },
                    },
                    "project": {
                        "data": {"id": "prj-abc123", "type": "projects"},
                    },
                },
            },
            {
                "id": "tprj-def456",
                "type": "team-projects",
                "attributes": {
                    "access": "read",
                    "project-access": {
                        "settings": "read",
                        "teams": "none",
                        "variable-sets": "none",
                    },
                    "workspace-access": {
                        "create": False,
                        "delete": False,
                        "move": False,
                        "locking": False,
                        "runs": "read",
                        "variables": "read",
                        "state-versions": "read",
                        "run-tasks": False,
                    },
                },
                "relationships": {
                    "team": {
                        "data": {"id": "team-456", "type": "teams"},
                    },
                },
            },
        ],
        "meta": {"pagination": {"total-count": 2}},
    }


@pytest.fixture
def team_detail_response():
    """Mock response for team details."""
    return {
        "data": {
            "id": "team-123",
            "type": "teams",
            "attributes": {
                "name": "backend-team",
                "description": "Backend engineering team",
                "created-at": "2025-01-15T08:00:00.000Z",
            },
            "relationships": {
                "organization": {
                    "data": {"id": "test-org", "type": "organizations"}
                }
            },
        }
    }


@pytest.fixture
def error_not_found():
    """Mock error response for not found."""
    return {
        "errors": [
            {
                "status": 404,
                "title": "not found",
                "detail": "Resource not found",
            }
        ]
    }


@pytest.fixture
def error_unauthorized():
    """Mock error response for unauthorized."""
    return {
        "errors": [
            {
                "status": 401,
                "title": "unauthorized",
                "detail": "Invalid or missing token",
            }
        ]
    }


@pytest.fixture
def error_forbidden():
    """Mock error response for forbidden."""
    return {
        "errors": [
            {
                "status": 403,
                "title": "forbidden",
                "detail": "Not authorized to access this resource",
            }
        ]
    }


# ============================================================================
# Workspace Clone Feature Fixtures
# ============================================================================


@pytest.fixture
def workspace_prod_response():
    """Mock response for prod-app workspace (source for cloning)."""
    return {
        "data": {
            "id": "ws-prod-abc123",
            "type": "workspaces",
            "attributes": {
                "name": "prod-app",
                "created-at": "2025-01-01T00:00:00.000Z",
                "updated-at": "2025-03-15T10:20:30.456Z",
                "terraform-version": "1.5.0",
                "execution-mode": "remote",
                "auto-apply": False,
                "locked": False,
                "tag-names": ["prod", "backend"],
                "vcs-repo": {
                    "identifier": "github.com/acme/terraform",
                    "branch": "main",
                    "repository-http-url": "https://github.com/acme/terraform",
                    "oauth-token-id": "ot-prod123",
                },
            },
        }
    }


@pytest.fixture
def workspace_prod_with_variables_response():
    """Mock response for prod-app workspace with 3 variables."""
    return {
        "data": {
            "id": "ws-prod-abc123",
            "type": "workspaces",
            "attributes": {
                "name": "prod-app",
                "created-at": "2025-01-01T00:00:00.000Z",
                "terraform-version": "1.5.0",
                "execution-mode": "remote",
                "auto-apply": False,
                "tag-names": ["prod"],
            },
        }
    }


@pytest.fixture
def workspace_variables_prod_response():
    """Mock response for prod-app workspace variables."""
    return {
        "data": [
            {
                "id": "var-1",
                "type": "vars",
                "attributes": {
                    "key": "environment",
                    "value": "production",
                    "category": "terraform",
                    "sensitive": False,
                    "hcl": False,
                },
            },
            {
                "id": "var-2",
                "type": "vars",
                "attributes": {
                    "key": "db_password",
                    "value": "***",
                    "category": "env",
                    "sensitive": True,
                    "hcl": False,
                },
            },
            {
                "id": "var-3",
                "type": "vars",
                "attributes": {
                    "key": "region_config",
                    "value": '{"regions": ["us-east-1", "us-west-2"]}',
                    "category": "terraform",
                    "sensitive": False,
                    "hcl": True,
                },
            },
        ],
        "meta": {"pagination": {"total-count": 3}},
    }


@pytest.fixture
def workspace_cloned_response():
    """Mock response for cloned workspace."""
    return {
        "data": {
            "id": "ws-staging-def456",
            "type": "workspaces",
            "attributes": {
                "name": "staging-app",
                "created-at": "2025-03-16T12:00:00.000Z",
                "terraform-version": "1.5.0",
                "execution-mode": "remote",
                "auto-apply": False,
                "tag-names": ["prod"],
            },
        }
    }


@pytest.fixture
def workspace_existing_target_response():
    """Mock response for existing target workspace."""
    return {
        "data": {
            "id": "ws-existing-xyz789",
            "type": "workspaces",
            "attributes": {
                "name": "existing-target",
                "created-at": "2025-02-01T08:00:00.000Z",
                "terraform-version": "1.4.0",
                "execution-mode": "remote",
                "auto-apply": True,
                "tag-names": ["test"],
            },
        }
    }


@pytest.fixture
def variable_create_response():
    """Mock response for created variable."""
    return {
        "data": {
            "id": "var-new123",
            "type": "vars",
            "attributes": {
                "key": "region",
                "value": "us-east-1",
                "category": "terraform",
                "sensitive": False,
                "hcl": False,
            },
        }
    }


# Log streaming fixtures
@pytest.fixture
def plan_log_empty():
    """Empty plan log (no content yet)."""
    return ""


@pytest.fixture
def plan_log_partial():
    """Plan log with partial content (planning in progress)."""
    return "Terraform v1.7.0\non linux (aarch64)\nConfiguring the remote state backend..."


@pytest.fixture
def plan_log_complete():
    """Plan log with full content (planning complete)."""
    return (
        "Terraform v1.7.0\n"
        "on linux (aarch64)\n"
        "Configuring the remote state backend...\n"
        "Terraform has been successfully initialized!\n"
        "Planning 2 to add, 0 to change, 0 to destroy"
    )


@pytest.fixture
def apply_log_complete():
    """Apply log with full content (apply complete)."""
    return (
        "aws_instance.web[0]: Creating...\n"
        "aws_instance.web[0]: Still creating... [10s elapsed]\n"
        "aws_instance.web[0]: Creation complete after 15s [id=i-0a1b2c3d4e5f6g7h8]\n"
        "aws_instance.web[1]: Creating...\n"
        "aws_instance.web[1]: Creation complete after 12s [id=i-0c5d6e7f8g9h0i1j2]\n"
        "Apply complete! Resources: 2 added, 0 changed, 0 destroyed"
    )


@pytest.fixture
def plan_log_with_error():
    """Plan log that ends with an error."""
    return (
        "Terraform v1.7.0\n"
        "on linux (aarch64)\n"
        "Error: Missing required argument\n"
        "on main.tf line 5, in resource \"aws_instance\" \"web\":\n"
        "5:   instance_type = var.missing_type\n"
        "The argument \"instance_type\" is required, but was not set"
    )


@pytest.fixture
def run_with_plan_id_response():
    """Mock run response with plan relationship."""
    return {
        "id": "run-plan-123",
        "type": "runs",
        "attributes": {
            "status": "planning",
            "created-at": "2025-04-01T10:00:00Z",
            "updated-at": "2025-04-01T10:01:00Z",
            "message": None,
            "auto-apply": False,
            "is-destroy": False,
        },
        "relationships": {
            "plan": {
                "data": {
                    "id": "plan-abc123",
                    "type": "plans",
                }
            }
        },
    }


@pytest.fixture
def run_with_apply_id_response():
    """Mock run response with both plan and apply relationships."""
    return {
        "id": "run-apply-456",
        "type": "runs",
        "attributes": {
            "status": "applying",
            "created-at": "2025-04-01T10:00:00Z",
            "updated-at": "2025-04-01T10:05:00Z",
            "message": None,
            "auto-apply": False,
            "is-destroy": False,
        },
        "relationships": {
            "plan": {
                "data": {
                    "id": "plan-abc123",
                    "type": "plans",
                }
            },
            "apply": {
                "data": {
                    "id": "apply-xyz789",
                    "type": "applies",
                }
            },
        },
    }
