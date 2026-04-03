"""Tests for Plan model and plan-related functionality."""

import pytest
from unittest.mock import MagicMock

from terrapyne.api.runs import RunsAPI
from terrapyne.models.plan import Plan


class TestPlanModel:
    """Test Plan model creation and attributes."""

    def test_plan_from_api_response(self):
        """Test creating a Plan from API response."""
        response = {
            "id": "plan-abc123",
            "type": "plans",
            "attributes": {
                "status": "finished",
                "has-changes": True,
                "resource-additions": 2,
                "resource-changes": 5,
                "resource-destructions": 1,
                "resource-imports": 0,
                "action-invocations": 0,
            },
        }

        plan = Plan.from_api_response(response)

        assert plan.id == "plan-abc123"
        assert plan.status == "finished"
        assert plan.has_changes is True
        assert plan.resource_additions == 2
        assert plan.resource_changes == 5
        assert plan.resource_destructions == 1
        assert plan.resource_imports == 0
        assert plan.action_invocations == 0

    def test_plan_with_no_changes(self):
        """Test Plan when has-changes is false."""
        response = {
            "id": "plan-no-changes",
            "type": "plans",
            "attributes": {
                "status": "finished",
                "has-changes": False,
                "resource-additions": 0,
                "resource-changes": 0,
                "resource-destructions": 0,
            },
        }

        plan = Plan.from_api_response(response)

        assert plan.has_changes is False
        assert plan.resource_additions == 0
        assert plan.resource_changes == 0
        assert plan.resource_destructions == 0

    def test_plan_with_defaults(self):
        """Test Plan uses defaults when attributes are missing."""
        response = {
            "id": "plan-minimal",
            "type": "plans",
            "attributes": {
                "status": "queued",
            },
        }

        plan = Plan.from_api_response(response)

        assert plan.id == "plan-minimal"
        assert plan.status == "queued"
        assert plan.has_changes is False
        assert plan.resource_additions == 0
        assert plan.resource_changes == 0
        assert plan.resource_destructions == 0

    def test_plan_with_large_change_counts(self):
        """Test Plan with large resource change counts."""
        response = {
            "id": "plan-large",
            "type": "plans",
            "attributes": {
                "status": "finished",
                "has-changes": True,
                "resource-additions": 100,
                "resource-changes": 500,
                "resource-destructions": 50,
            },
        }

        plan = Plan.from_api_response(response)

        assert plan.resource_additions == 100
        assert plan.resource_changes == 500
        assert plan.resource_destructions == 50


class TestGetPlan:
    """Test fetching plan details via API."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create RunsAPI instance with mock client."""
        return RunsAPI(mock_client)

    def test_get_plan_basic(self, api, mock_client):
        """Test fetching a plan by ID."""
        plan_id = "plan-xyz789"
        response = {
            "id": plan_id,
            "type": "plans",
            "attributes": {
                "status": "finished",
                "has-changes": True,
                "resource-additions": 3,
                "resource-changes": 8,
                "resource-destructions": 0,
            },
        }
        mock_client.get.return_value = {"data": response}

        plan = api.get_plan(plan_id)

        # Verify API call
        mock_client.get.assert_called_once_with(f"/plans/{plan_id}")

        # Verify returned plan
        assert isinstance(plan, Plan)
        assert plan.id == plan_id
        assert plan.status == "finished"
        assert plan.resource_changes == 8

    def test_get_plan_with_no_changes(self, api, mock_client):
        """Test fetching a plan with no resource changes."""
        plan_id = "plan-no-change"
        response = {
            "id": plan_id,
            "type": "plans",
            "attributes": {
                "status": "finished",
                "has-changes": False,
                "resource-additions": 0,
                "resource-changes": 0,
                "resource-destructions": 0,
            },
        }
        mock_client.get.return_value = {"data": response}

        plan = api.get_plan(plan_id)

        assert plan.has_changes is False
        assert plan.resource_changes == 0

    def test_get_plan_with_destructions(self, api, mock_client):
        """Test fetching a plan that destroys resources."""
        plan_id = "plan-destroy"
        response = {
            "id": plan_id,
            "type": "plans",
            "attributes": {
                "status": "finished",
                "has-changes": True,
                "resource-additions": 0,
                "resource-changes": 2,
                "resource-destructions": 5,
            },
        }
        mock_client.get.return_value = {"data": response}

        plan = api.get_plan(plan_id)

        assert plan.resource_additions == 0
        assert plan.resource_changes == 2
        assert plan.resource_destructions == 5
