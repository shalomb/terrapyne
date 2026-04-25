"""Tests for TFCClient response caching."""

import hashlib
import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from terrapyne.api.client import TFCClient


@pytest.fixture
def mock_creds():
    with patch("terrapyne.core.credentials.TerraformCredentials.load") as m:
        m.return_value = MagicMock()
        m.return_value.get_headers.return_value = {"Authorization": "Bearer XXX"}
        yield m


@pytest.fixture
def temp_cache_dir(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    # Patch Path.expanduser to return our temp dir
    # We also need to patch Path("~/.terrapyne/cache") in client.py
    with patch("terrapyne.api.client.Path") as mock_path:
        mock_path.return_value.expanduser.return_value = cache_dir
        # Ensure mkdir and other methods work on the mock
        mock_path.side_effect = lambda *args: (
            Path(*args) if "~" not in str(args) else MagicMock(expanduser=lambda: cache_dir)
        )
        yield cache_dir


def test_cache_hit(mock_creds, tmp_path):
    """Test that a cache hit returns cached data and avoids API call."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    with patch("terrapyne.api.client.Path") as mock_path:
        # Mock Path("~/.terrapyne/cache").expanduser()
        mock_expandable = MagicMock()
        mock_expandable.expanduser.return_value = cache_dir

        def path_mock_init(p):
            if p == "~/.terrapyne/cache":
                return mock_expandable
            return Path(p)

        mock_path.side_effect = path_mock_init

        client = TFCClient(credentials=mock_creds, cache_ttl=60)

        # Pre-populate cache
        url = f"{client.base_url}/workspaces"
        params = {"limit": 10}
        key_content = f"GET:{url}:{json.dumps(params, sort_keys=True)}"
        key = hashlib.md5(key_content.encode()).hexdigest()
        cache_file = cache_dir / f"{key}.json"
        cached_data = {"data": [{"id": "ws-cached"}]}

        with open(cache_file, "w") as f:
            json.dump(cached_data, f)

        with patch.object(TFCClient, "_request") as mock_request:
            result = client.get("/workspaces", params=params)

            assert result == cached_data
            mock_request.assert_not_called()


def test_cache_miss_and_populate(mock_creds, tmp_path):
    """Test that a cache miss triggers API call and populates cache."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    with patch("terrapyne.api.client.Path") as mock_path:
        mock_expandable = MagicMock()
        mock_expandable.expanduser.return_value = cache_dir
        mock_path.side_effect = lambda p: mock_expandable if p == "~/.terrapyne/cache" else Path(p)

        client = TFCClient(credentials=mock_creds, cache_ttl=60)
        api_data = {"data": [{"id": "ws-live"}]}

        with patch.object(TFCClient, "_request") as mock_request:
            mock_request.return_value.json.return_value = api_data

            result = client.get("/workspaces")

            assert result == api_data
            mock_request.assert_called_once()

            # Verify cache file exists
            files = list(cache_dir.glob("*.json"))
            assert len(files) == 1
            with open(files[0]) as f:
                assert json.load(f) == api_data


def test_cache_expiration(mock_creds, tmp_path):
    """Test that expired cache triggers a new API call."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    with patch("terrapyne.api.client.Path") as mock_path:
        mock_expandable = MagicMock()
        mock_expandable.expanduser.return_value = cache_dir
        mock_path.side_effect = lambda p: mock_expandable if p == "~/.terrapyne/cache" else Path(p)

        client = TFCClient(credentials=mock_creds, cache_ttl=1)  # 1 second TTL

        # Pre-populate cache with old timestamp
        url = f"{client.base_url}/workspaces"
        key_content = f"GET:{url}:{json.dumps(None, sort_keys=True)}"
        key = hashlib.md5(key_content.encode()).hexdigest()
        cache_file = cache_dir / f"{key}.json"

        with open(cache_file, "w") as f:
            json.dump({"old": "data"}, f)

        # Set mtime to 2 seconds ago
        old_time = time.time() - 2
        os.utime(cache_file, (old_time, old_time))

        api_data = {"new": "data"}
        with patch.object(TFCClient, "_request") as mock_request:
            mock_request.return_value.json.return_value = api_data

            result = client.get("/workspaces")

            assert result == api_data
            mock_request.assert_called_once()
