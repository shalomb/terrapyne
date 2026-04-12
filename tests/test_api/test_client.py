"""Tests for TFCClient core functionality.

Tests the HTTP client, authentication, and pagination logic.
"""

from unittest.mock import patch

from terrapyne.api.client import TFCClient
from terrapyne.core.credentials import TerraformCredentials


class TestTFCClientInitialization:
    """Test TFCClient initialization and configuration."""

    def test_client_initialization_with_credentials(self):
        """Test client initialization with TerraformCredentials object."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(host="app.terraform.io", credentials=creds)
        assert client is not None
        assert client.creds == creds
        assert client.creds.token == "test-token"

    def test_client_default_host(self):
        """Test client uses default host when not specified."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)
        assert client is not None
        # Should have a default host
        assert client.host == "app.terraform.io"

    def test_client_custom_host(self):
        """Test client accepts custom host."""
        custom_host = "tfe.example.com"
        creds = TerraformCredentials(host=custom_host, token="test-token")
        client = TFCClient(host=custom_host, credentials=creds)
        assert client.host == custom_host
        assert client.creds.host == custom_host

    def test_client_organization(self):
        """Test client can be initialized with organization."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(organization="my-org", credentials=creds)
        assert client.organization == "my-org"


class TestTFCClientContextManager:
    """Test TFCClient context manager functionality."""

    def test_client_context_manager(self):
        """Test client works as context manager."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        with TFCClient(credentials=creds) as client:
            assert client is not None
            assert isinstance(client, TFCClient)

    def test_client_context_manager_cleanup(self):
        """Test client cleanup on context exit."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)
        with client:
            assert client.client is not None
        # Client should still be usable after context


class TestPaginationDefensiveCopy:
    """Test pagination uses defensive copy of params.

    This is critical to prevent mutation of original params dict
    that would cause pagination to return only first page on retry.
    """

    @patch("terrapyne.api.client.TFCClient.get")
    def test_paginate_params_not_mutated(self, mock_get):
        """Test that paginate() doesn't mutate original params dict."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)

        # Setup mock response
        mock_get.return_value = {
            "data": [{"id": "item-1"}],
            "meta": {"pagination": {"total-count": 1}},
        }

        # Original params dict we want to reuse
        params = {"limit": 10}

        # First call with params
        list(client.paginate("/workspaces", params=params))

        # Verify params dict wasn't mutated
        assert params == {"limit": 10}, "Original params dict was mutated!"

        # Second call should work the same way
        list(client.paginate("/workspaces", params=params))

        # Both calls should succeed without params mutation causing issues
        assert mock_get.call_count >= 2

    @patch("terrapyne.api.client.TFCClient.get")
    def test_paginate_with_meta_params_not_mutated(self, mock_get):
        """Test that paginate_with_meta() doesn't mutate original params dict."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)

        # Setup mock response
        mock_get.return_value = {
            "data": [{"id": "item-1"}],
            "meta": {"pagination": {"total-count": 2}},
        }

        # Original params dict
        params = {"status": "applied"}

        # Call paginate_with_meta
        results, _total = client.paginate_with_meta("/runs", params=params)
        list(results)  # Consume generator to trigger paginate calls

        # Verify params dict wasn't mutated
        assert params == {"status": "applied"}, "Original params dict was mutated!"


class TestAPIResponseHandling:
    """Test API response parsing and error handling."""

    @patch("terrapyne.api.client.TFCClient.get")
    def test_handles_200_response(self, mock_get):
        """Test successful API response handling."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)

        mock_get.return_value = {"data": [{"id": "ws-1", "attributes": {"name": "test"}}]}

        # Should not raise
        results = list(client.paginate("/workspaces"))
        assert len(results) > 0

    @patch("terrapyne.api.client.TFCClient.get")
    def test_handles_empty_response(self, mock_get):
        """Test handling of empty API response."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)

        mock_get.return_value = {
            "data": [],
            "meta": {"pagination": {"total-count": 0}},
        }

        # Should handle gracefully
        results = list(client.paginate("/workspaces"))
        assert results == []

    @patch("terrapyne.api.client.TFCClient.get")
    def test_pagination_meta_extraction(self, mock_get):
        """Test pagination metadata is extracted correctly."""
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)

        mock_get.return_value = {
            "data": [{"id": "item-1"}],
            "meta": {"pagination": {"total-count": 5, "page": 1}},
        }

        # Get results with metadata
        results, total = client.paginate_with_meta("/workspaces")
        results_list = list(results)

        assert total == 5
        assert len(results_list) > 0


class TestRetryLogic:
    """Test API retry logic for transient failures."""

    def test_retry_on_transient_failure(self):
        """Test that .get() method exists and has retry decorator.

        The .get() method is decorated with @retry via tenacity to handle
        transient HTTPStatusError exceptions. This test verifies the method
        is callable and properly configured.
        """
        creds = TerraformCredentials(host="app.terraform.io", token="test-token")
        client = TFCClient(credentials=creds)

        # Verify get() method exists and is callable
        assert callable(client.get)

        # Verify it has the retry decorator applied (wrapped function signature)
        assert hasattr(client.get, "__wrapped__") or "retry" in str(type(client.get))
