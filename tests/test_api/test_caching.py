"""Tests for TFC API response caching."""
import pytest
import time
from unittest.mock import MagicMock, patch
from terrapyne.api.client import TFCClient
from terrapyne.core.credentials import TerraformCredentials

@pytest.fixture
def mock_creds():
    creds = MagicMock(spec=TerraformCredentials)
    creds.get_headers.return_value = {"Authorization": "Bearer test-token"}
    return creds

def test_get_caching(monkeypatch, tmp_path, mock_creds):
    """Repeated GET requests within TTL should use cache."""
    # Mock home directory for cache
    monkeypatch.setenv("HOME", str(tmp_path))
    
    with patch("httpx.Client.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test-data"}
        mock_get.return_value = mock_response
        
        client = TFCClient(organization="test-org", credentials=mock_creds)
        
        # First call: should call API
        res1 = client.get("/test", params={"foo": "bar"}, use_cache=True)
        assert res1 == {"data": "test-data"}
        assert mock_get.call_count == 1
        
        # Second call: should use cache
        res2 = client.get("/test", params={"foo": "bar"}, use_cache=True)
        assert res2 == {"data": "test-data"}
        assert mock_get.call_count == 1
        
        # Call with different params: should call API
        res3 = client.get("/test", params={"foo": "baz"}, use_cache=True)
        assert res3 == {"data": "test-data"}
        assert mock_get.call_count == 2

def test_cache_invalidation(monkeypatch, tmp_path, mock_creds):
    """POST request should invalidate cache."""
    monkeypatch.setenv("HOME", str(tmp_path))
    
    with patch("httpx.Client.get") as mock_get, \
         patch("httpx.Client.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test-data"}
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        client = TFCClient(organization="test-org", credentials=mock_creds)
        
        # Fill cache
        client.get("/test")
        assert mock_get.call_count == 1
        
        # POST call: should invalidate
        client.post("/test-action", json_data={"foo": "bar"})
        assert mock_post.call_count == 1
        
        # Next GET: should call API again
        client.get("/test")
        assert mock_get.call_count == 2
