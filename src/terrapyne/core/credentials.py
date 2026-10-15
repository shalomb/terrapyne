"""Terraform Cloud credentials management."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TerraformCredentials(BaseModel):
    """Terraform credentials."""

    host: str = Field(default="app.terraform.io")
    token: str

    @classmethod
    def load(
        cls,
        host: str = "app.terraform.io",
        tfrc_path: Path | None = None,
        profile: Any | None = None,
    ) -> "TerraformCredentials":
        """Load from credentials file, profile, or environment variable.

        Priority (12-factor compliant):
        1. TFC_TOKEN environment variable (highest)
        2. Profile token_env or token (if specified)
        3. TFRC environment variable (file path)
        4. Default ~/.terraform.d/credentials.tfrc.json (lowest)
        """
        # Check for direct token in environment variable first
        if "TFC_TOKEN" in os.environ:
            token = os.environ["TFC_TOKEN"]
            return cls(host=host, token=token)

        # Check for token in active profile
        if profile is not None:
            token_env = getattr(profile, "token_env", None)
            if token_env and token_env in os.environ:
                return cls(host=host, token=os.environ[token_env])
            token_val = getattr(profile, "token", None)
            if token_val:
                return cls(host=host, token=token_val)

        if tfrc_path is None:
            tfrc_path = Path.home() / ".terraform.d" / "credentials.tfrc.json"

        # Support TFRC env var
        if "TFRC" in os.environ:
            tfrc_path = Path(os.path.expanduser(os.environ["TFRC"]))

        if not tfrc_path.exists():
            raise FileNotFoundError(
                f"Terraform credentials file not found: {tfrc_path}\n"
                f"Run 'terraform login' to create it."
            ) from None

        with open(tfrc_path) as f:
            data = json.load(f)

        try:
            token = data["credentials"][host]["token"]
        except KeyError:
            available = list(data.get("credentials", {}).keys())
            raise KeyError(
                f"No credentials for host '{host}' in {tfrc_path}\nAvailable hosts: {available}"
            ) from None

        return cls(host=host, token=token)

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/vnd.api+json",
        }
