#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""Terrapyne exception hierarchy."""

from typing import Any


class TerrapyneError(Exception):
    """Base exception for all Terrapyne errors."""

    pass


# --- Local Terraform Binary Errors ---


class TerraformError(TerrapyneError):
    """Base exception for local Terraform binary errors."""

    pass


class TerraformVersionError(TerraformError):
    """Raised when Terraform version is incorrect or missing."""

    pass


class TerraformApplyError(TerraformError):
    """Raised when 'terraform apply' (or other command) fails."""

    def __init__(self, message, exit_code, expect_exit_code, stdout, stderr, pwd):
        self.message = message
        self.exit_code = exit_code
        self.expect_exit_code = expect_exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.pwd = pwd
        super().__init__(self.message)


# Backwards compatible aliases
TerraformVersionException = TerraformVersionError
TerraformApplyException = TerraformApplyError


# --- TFC API Errors ---


class TFCAPIError(TerrapyneError):
    """Base exception for TFC API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: Any | None = None,
    ):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class TFCAuthenticationError(TFCAPIError):
    """Raised on 401 Unauthorized or 403 Forbidden."""

    pass


class TFCNotFoundError(TFCAPIError):
    """Raised on 404 Not Found."""

    pass


class TFCConflictError(TFCAPIError):
    """Raised on 409 Conflict."""

    pass


class TFCRateLimitError(TFCAPIError):
    """Raised on 429 Too Many Requests."""

    pass


class TFCServerError(TFCAPIError):
    """Raised on 5xx Server Errors."""

    pass


# --- Workspace Specific Errors ---


class WorkspaceNotFoundError(TFCNotFoundError):
    """Raised when a workspace is not found."""

    pass


class WorkspaceAlreadyExistsError(TFCConflictError):
    """Raised when a workspace already exists."""

    pass


class VCSTokenRequiredError(TFCAPIError):
    """Raised when a VCS token ID is required for a cross-org clone."""

    pass
