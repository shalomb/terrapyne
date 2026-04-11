"""Terraform Cloud API client."""

import hashlib
import json
import time
from collections.abc import Callable, Iterator
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from terrapyne.core.credentials import TerraformCredentials

if TYPE_CHECKING:
    from terrapyne.api.projects import ProjectAPI
    from terrapyne.api.runs import RunsAPI
    from terrapyne.api.state_versions import StateVersionsAPI
    from terrapyne.api.teams import TeamsAPI
    from terrapyne.api.workspaces import WorkspaceAPI


class TFCClient:
    """Terraform Cloud API client with retry logic and pagination support."""

    def __init__(
        self,
        host: str = "app.terraform.io",
        organization: str | None = None,
        credentials: TerraformCredentials | None = None,
        debug: bool | None = None,
    ):
        """Initialize TFC client.

        Args:
            host: TFC hostname (default: app.terraform.io)
            organization: TFC organization name
            credentials: Optional pre-loaded credentials (otherwise loaded from tfrc.json)
            debug: Enable API call tracing (defaults to global CLI debug state)
        """
        self.host = host
        self.organization = organization
        self.creds = credentials or TerraformCredentials.load(host=host)
        self.base_url = f"https://{host}/api/v2"

        if debug is None:
            try:
                from terrapyne.cli.utils import is_debug

                debug = is_debug()
            except ImportError:
                debug = False

        self.debug = debug

        self._cache_dir = Path.home() / ".cache" / "terrapyne"
        self._cache_ttl = 300  # 5 minutes

        event_hooks: dict[str, list[Callable[..., Any]]] = {}
        if debug:
            event_hooks = {
                "request": [self._log_request],
                "response": [self._log_response],
            }

        self.client = httpx.Client(
            headers=self.creds.get_headers(),
            timeout=30.0,
            follow_redirects=True,
            event_hooks=event_hooks,  # type: ignore[arg-type]
        )

    def _log_request(self, request: httpx.Request) -> None:
        """Log API request for debugging."""
        print(f"\n[DEBUG] API Request: {request.method} {request.url}")
        if request.content:
            try:
                import json

                body = json.loads(request.content)
                print(f"[DEBUG] Body: {json.dumps(body, indent=2)}")
            except Exception:
                print(f"[DEBUG] Body: {request.content!r}")

    def _log_response(self, response: httpx.Response) -> None:
        """Log API response for debugging."""
        print(f"[DEBUG] API Response: {response.status_code}")
        try:
            import json

            body = response.json()
            print(f"[DEBUG] Response: {json.dumps(body, indent=2)}")
        except Exception:
            if response.text:
                print(f"[DEBUG] Response (text): {response.text[:500]}...")

    def _get_cache_key(self, path: str, params: dict[str, Any] | None = None) -> str:
        """Generate a stable cache key for a request."""
        # Include organization in key if set
        org = self.organization or "no-org"
        key_data = f"{org}:{path}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _invalidate_cache(self) -> None:
        """Clear all cached responses."""
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                with suppress(Exception):
                    f.unlink()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "TFCClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    @property
    def workspaces(self) -> "WorkspaceAPI":
        """Get workspace API instance."""
        from terrapyne.api.workspaces import WorkspaceAPI

        return WorkspaceAPI(self)

    @property
    def runs(self) -> "RunsAPI":
        """Get runs API instance."""
        from terrapyne.api.runs import RunsAPI

        return RunsAPI(self)

    @property
    def projects(self) -> "ProjectAPI":
        """Get project API instance."""
        from terrapyne.api.projects import ProjectAPI

        return ProjectAPI(self)

    @property
    def teams(self) -> "TeamsAPI":
        """Get teams API instance."""
        from terrapyne.api.teams import TeamsAPI

        return TeamsAPI(self)

    @property
    def state_versions(self) -> "StateVersionsAPI":
        """Get state versions API instance."""
        from terrapyne.api.state_versions import StateVersionsAPI

        return StateVersionsAPI(self)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def get(
        self, path: str, params: dict[str, Any] | None = None, use_cache: bool = True
    ) -> dict[str, Any]:
        """GET request with retry logic and optional caching.

        Args:
            path: API path (e.g., "/organizations/my-org/workspaces")
            params: Query parameters
            use_cache: Whether to use local response cache

        Returns:
            JSON response dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
        """
        cache_key = self._get_cache_key(path, params)
        cache_file = self._cache_dir / f"{cache_key}.json"

        if use_cache and cache_file.exists():
            try:
                with open(cache_file) as f:
                    cache_data = json.load(f)
                    if time.time() - cache_data["timestamp"] < self._cache_ttl:
                        return cache_data["response"]
            except Exception:
                pass

        url = f"{self.base_url}{path}"
        response = self.client.get(url, params=params or {})
        response.raise_for_status()
        data = response.json()

        # Update cache
        if use_cache:
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "w") as f:
                    json.dump({"timestamp": time.time(), "response": data}, f)
            except Exception:
                pass

        return data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def post(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST request with retry logic.

        Args:
            path: API path
            json_data: JSON payload

        Returns:
            JSON response dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
        """
        self._invalidate_cache()
        url = f"{self.base_url}{path}"
        response = self.client.post(url, json=json_data or {})
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def patch(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """PATCH request with retry logic.

        Args:
            path: API path
            json_data: JSON payload

        Returns:
            JSON response dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
        """
        self._invalidate_cache()
        url = f"{self.base_url}{path}"
        response = self.client.patch(url, json=json_data or {})
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def delete(self, path: str) -> dict[str, Any]:
        """DELETE request with retry logic.

        Args:
            path: API path

        Returns:
            JSON response dict (usually empty for DELETE)

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
        """
        self._invalidate_cache()
        url = f"{self.base_url}{path}"
        response = self.client.delete(url)
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    def paginate(
        self, path: str, params: dict[str, Any] | None = None, page_size: int = 100
    ) -> Iterator[dict[str, Any]]:
        """Paginate through API results.

        Args:
            path: API path
            params: Query parameters
            page_size: Items per page (max 100)

        Yields:
            Individual items from paginated results
        """
        params = (params or {}).copy()
        page = 1

        while True:
            params.update({"page[number]": page, "page[size]": min(page_size, 100)})
            response_data = self.get(path, params=params)

            # Yield items from current page
            data = response_data.get("data", [])
            if not data:
                break

            yield from data

            # Check if there are more pages
            links = response_data.get("links", {})
            if not links.get("next"):
                break

            page += 1

    def paginate_with_meta(
        self, path: str, params: dict[str, Any] | None = None, page_size: int = 100
    ) -> tuple[Iterator[dict[str, Any]], int | None]:
        """Paginate through API results with metadata.

        Args:
            path: API path
            params: Query parameters
            page_size: Items per page (max 100)

        Returns:
            Tuple of (iterator of items, total count from meta or None)
        """
        params = (params or {}).copy()
        params.update({"page[number]": 1, "page[size]": min(page_size, 100)})

        # Get first page to extract total count
        first_response = self.get(path, params=params)

        # Extract total count from meta
        total_count = None
        meta = first_response.get("meta", {})
        pagination = meta.get("pagination", {})
        total_count = pagination.get("total-count")

        # Generator to yield items from all pages
        def item_iterator() -> Iterator[dict[str, Any]]:
            # Yield items from first page
            data = first_response.get("data", [])
            yield from data

            # Continue with remaining pages if there are any
            links = first_response.get("links", {})
            if links.get("next"):
                page = 2
                while True:
                    params["page[number]"] = page
                    response_data = self.get(path, params=params)

                    data = response_data.get("data", [])
                    if not data:
                        break

                    yield from data

                    links = response_data.get("links", {})
                    if not links.get("next"):
                        break

                    page += 1

        return item_iterator(), total_count

    def get_organization(self, org: str | None = None) -> str:
        """Get organization name (from param, instance, or raise error).

        Args:
            org: Optional organization name

        Returns:
            Organization name

        Raises:
            ValueError: If no organization specified
        """
        organization = org or self.organization
        if not organization:
            raise ValueError(
                "Organization not specified. "
                "Pass --organization or set it in client initialization."
            )
        return organization
