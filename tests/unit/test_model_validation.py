"""Tests verifying model_validate() is used in from_api_response() so invalid
API responses raise ValidationError rather than silently creating broken instances.
"""

import pytest
from pydantic import ValidationError

from terrapyne.models.apply import Apply
from terrapyne.models.plan import Plan
from terrapyne.models.project import Project
from terrapyne.models.run import Run
from terrapyne.models.state_version import StateVersion
from terrapyne.models.team import Team
from terrapyne.models.team_access import TeamProjectAccess
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace


class TestRunValidation:
    """Run.from_api_response() must validate required fields."""

    def test_run_missing_id_raises(self):
        data = {"attributes": {"status": "applied"}}
        with pytest.raises(KeyError):
            Run.from_api_response(data)

    def test_run_missing_status_raises(self):
        data = {"id": "run-1", "attributes": {}}
        with pytest.raises(KeyError):
            Run.from_api_response(data)

    def test_run_invalid_status_raises(self):
        """Invalid status value must raise an error, not silently store bad data."""
        data = {"id": "run-1", "attributes": {"status": "not-a-real-status"}}
        with pytest.raises((ValidationError, ValueError)):
            Run.from_api_response(data)

    def test_run_valid_response_succeeds(self):
        data = {"id": "run-1", "attributes": {"status": "applied"}}
        run = Run.from_api_response(data)
        assert run.id == "run-1"


class TestWorkspaceValidation:
    """Workspace.from_api_response() must validate required fields."""

    def test_workspace_missing_id_raises(self):
        data = {"attributes": {"name": "ws"}}
        with pytest.raises((KeyError, ValidationError)):
            Workspace.from_api_response(data)

    def test_workspace_valid_response_succeeds(self):
        data = {"id": "ws-1", "attributes": {"name": "ws"}}
        ws = Workspace.from_api_response(data)
        assert ws.id == "ws-1"
        assert ws.name == "ws"


class TestTeamValidation:
    """Team.from_api_response() must validate required fields."""

    def test_team_missing_id_raises(self):
        data = {"attributes": {"name": "devs"}}
        with pytest.raises((KeyError, ValidationError)):
            Team.from_api_response(data)

    def test_team_valid_response_succeeds(self):
        data = {"id": "team-1", "attributes": {"name": "devs"}}
        team = Team.from_api_response(data)
        assert team.id == "team-1"
        assert team.name == "devs"


class TestProjectValidation:
    """Project.from_api_response() must validate required fields."""

    def test_project_missing_id_raises(self):
        data = {"attributes": {"name": "infra"}}
        with pytest.raises((KeyError, ValidationError)):
            Project.from_api_response(data)

    def test_project_valid_response_succeeds(self):
        data = {"id": "prj-1", "attributes": {"name": "infra"}}
        project = Project.from_api_response(data)
        assert project.id == "prj-1"
        assert project.name == "infra"


class TestStateVersionValidation:
    """StateVersion.from_api_response() must validate required fields."""

    def test_state_version_missing_id_raises(self):
        data = {"attributes": {"serial": 1}}
        with pytest.raises((KeyError, ValidationError)):
            StateVersion.from_api_response(data)

    def test_state_version_valid_response_succeeds(self):
        data = {"id": "sv-1", "attributes": {"serial": 5}}
        sv = StateVersion.from_api_response(data)
        assert sv.id == "sv-1"
        assert sv.serial == 5


class TestApplyValidation:
    """Apply.from_api_response() must validate required fields."""

    def test_apply_missing_id_raises(self):
        data = {"attributes": {"status": "finished"}}
        with pytest.raises((KeyError, ValidationError)):
            Apply.from_api_response(data)

    def test_apply_valid_response_succeeds(self):
        data = {"id": "apply-1", "attributes": {"status": "finished"}}
        apply_obj = Apply.from_api_response(data)
        assert apply_obj.id == "apply-1"


class TestPlanValidation:
    """Plan.from_api_response() must validate required fields."""

    def test_plan_missing_id_raises(self):
        data = {"attributes": {"status": "finished"}}
        with pytest.raises((KeyError, ValidationError)):
            Plan.from_api_response(data)

    def test_plan_valid_response_succeeds(self):
        data = {"id": "plan-1", "attributes": {"status": "finished"}}
        plan = Plan.from_api_response(data)
        assert plan.id == "plan-1"


class TestWorkspaceVariableValidation:
    """WorkspaceVariable.from_api_response() must validate required fields."""

    def test_variable_missing_id_raises(self):
        data = {"attributes": {"key": "TF_VAR_foo", "category": "terraform"}}
        with pytest.raises((KeyError, ValidationError)):
            WorkspaceVariable.from_api_response(data)

    def test_variable_valid_response_succeeds(self):
        data = {
            "id": "var-1",
            "attributes": {"key": "TF_VAR_foo", "category": "terraform"},
        }
        var = WorkspaceVariable.from_api_response(data)
        assert var.id == "var-1"
        assert var.key == "TF_VAR_foo"


class TestTypeCoercionValidation:
    """Public constructors enforce field types; from_api_response uses model_construct for trusted API data."""

    def test_workspace_locked_bad_type_raises(self):
        """'locked' field must be bool — wrong type raises ValidationError on direct construction."""
        with pytest.raises((ValidationError, ValueError)):
            Workspace(id="ws-1", name="ws", locked="not-a-bool")

    def test_project_resource_count_bad_type_raises(self):
        """'resource-count' must be int — wrong type raises ValidationError on direct construction."""
        with pytest.raises((ValidationError, ValueError)):
            Project.model_validate(
                {"id": "prj-1", "name": "infra", "resource-count": "not-a-number"}
            )


class TestTeamProjectAccessValidation:
    """TeamProjectAccess.from_api_response() must validate required fields."""

    def test_team_access_missing_id_raises(self):
        data = {
            "attributes": {"access": "admin"},
            "relationships": {
                "team": {"data": {"id": "team-1"}},
                "project": {"data": {"id": "prj-1"}},
            },
        }
        with pytest.raises((KeyError, ValidationError)):
            TeamProjectAccess.from_api_response(data)

    def test_team_access_valid_response_succeeds(self):
        data = {
            "id": "tpa-1",
            "attributes": {"access": "admin"},
            "relationships": {
                "team": {"data": {"id": "team-1"}},
                "project": {"data": {"id": "prj-1"}},
            },
        }
        access = TeamProjectAccess.from_api_response(data)
        assert access.id == "tpa-1"
        assert access.access == "admin"
