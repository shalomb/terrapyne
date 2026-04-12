"""Tests for credential loading edge cases."""

import json
import os
from unittest.mock import patch

import pytest

from terrapyne.core.credentials import TerraformCredentials


class TestCredentialLoading:
    def test_load_from_tfc_token_env(self):
        with patch.dict(os.environ, {"TFC_TOKEN": "test-token-123"}, clear=False):
            creds = TerraformCredentials.load()
            assert creds.token == "test-token-123"

    def test_load_from_tfrc_env(self, tmp_path):
        tfrc = tmp_path / "creds.json"
        tfrc.write_text(
            json.dumps({"credentials": {"app.terraform.io": {"token": "tfrc-env-token"}}})
        )
        with patch.dict(os.environ, {"TFRC": str(tfrc)}, clear=False):
            os.environ.pop("TFC_TOKEN", None)
            creds = TerraformCredentials.load()
            assert creds.token == "tfrc-env-token"

    def test_load_missing_file_raises(self, tmp_path):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TFC_TOKEN", None)
            os.environ.pop("TFRC", None)
            with pytest.raises(FileNotFoundError, match="credentials file not found"):
                TerraformCredentials.load(tfrc_path=tmp_path / "nonexistent.json")
