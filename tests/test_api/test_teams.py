"""Tests for TeamsAPI methods."""

import pytest
from unittest.mock import MagicMock, patch

from terrapyne.api.teams import TeamsAPI
from terrapyne.models.team import Team


class TestTeamRetrieval:
    """Test team retrieval operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create TeamsAPI instance with mock client."""
        return TeamsAPI(mock_client)

    @pytest.fixture
    def sample_team_response(self):
        """Sample TFC API response for a team."""
        return {
            "id": "team-abc123",
            "type": "teams",
            "attributes": {
                "name": "Platform Team",
                "description": "Infrastructure and platform engineers",
                "created-at": "2024-01-10T10:00:00Z",
                "updated-at": "2024-01-15T14:30:00Z",
                "users-count": 5,
            },
        }

    def test_get_team(self, api, mock_client, sample_team_response):
        """Test retrieving a team by ID."""
        team_id = "team-abc123"
        mock_client.get.return_value = {"data": sample_team_response}

        team = api.get(team_id)

        # Verify API call
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[0][0] == f"/teams/{team_id}"

        # Verify returned team
        assert isinstance(team, Team)
        assert team.id == "team-abc123"
        assert team.name == "Platform Team"
        assert team.members_count == 5

    def test_list_teams(self, api, mock_client):
        """Test listing teams in organization."""
        org = "my-org"
        mock_client.get_organization.return_value = org

        response_items = [
            {
                "id": "team-1",
                "type": "teams",
                "attributes": {
                    "name": "Platform Team",
                    "description": "Infrastructure",
                    "created-at": "2024-01-10T10:00:00Z",
                    "updated-at": "2024-01-15T14:30:00Z",
                    "users-count": 5,
                },
            },
            {
                "id": "team-2",
                "type": "teams",
                "attributes": {
                    "name": "Application Team",
                    "description": "App development",
                    "created-at": "2024-01-12T10:00:00Z",
                    "updated-at": "2024-01-15T14:30:00Z",
                    "users-count": 8,
                },
            },
        ]

        mock_client.paginate_with_meta.return_value = (iter(response_items), 2)

        teams_iter, total_count = api.list_teams(organization=org)
        teams = list(teams_iter)

        # Verify organization resolution
        mock_client.get_organization.assert_called_once_with(org)

        # Verify pagination call
        mock_client.paginate_with_meta.assert_called_once()
        call_args = mock_client.paginate_with_meta.call_args
        assert call_args[0][0] == f"/organizations/{org}/teams"

        # Verify returned teams
        assert len(teams) == 2
        assert teams[0].id == "team-1"
        assert teams[0].name == "Platform Team"
        assert teams[1].id == "team-2"
        assert teams[1].name == "Application Team"
        assert total_count == 2


class TestTeamCreation:
    """Test team creation operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create TeamsAPI instance with mock client."""
        return TeamsAPI(mock_client)

    def test_create_team_basic(self, api, mock_client):
        """Test creating a basic team."""
        org = "my-org"
        mock_client.get_organization.return_value = org

        response = {
            "id": "team-new123",
            "type": "teams",
            "attributes": {
                "name": "New Team",
                "description": None,
                "created-at": "2024-01-20T10:00:00Z",
                "updated-at": "2024-01-20T10:00:00Z",
                "users-count": 0,
            },
        }
        mock_client.post.return_value = {"data": response}

        team = api.create(organization=org, name="New Team")

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"/organizations/{org}/teams"

        # Verify payload
        payload = call_args[1]["json_data"]
        assert payload["data"]["type"] == "teams"
        assert payload["data"]["attributes"]["name"] == "New Team"

        # Verify returned team
        assert team.id == "team-new123"
        assert team.name == "New Team"

    def test_create_team_with_description(self, api, mock_client):
        """Test creating a team with description."""
        org = "my-org"
        mock_client.get_organization.return_value = org

        response = {
            "id": "team-desc123",
            "type": "teams",
            "attributes": {
                "name": "DevOps Team",
                "description": "DevOps and infrastructure",
                "created-at": "2024-01-20T10:00:00Z",
                "updated-at": "2024-01-20T10:00:00Z",
                "users-count": 0,
            },
        }
        mock_client.post.return_value = {"data": response}

        team = api.create(
            organization=org,
            name="DevOps Team",
            description="DevOps and infrastructure",
        )

        # Verify description in payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["description"] == "DevOps and infrastructure"

        # Verify returned team
        assert team.description == "DevOps and infrastructure"


class TestTeamUpdate:
    """Test team update operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create TeamsAPI instance with mock client."""
        return TeamsAPI(mock_client)

    def test_update_team_name(self, api, mock_client):
        """Test updating team name."""
        team_id = "team-update123"
        response = {
            "id": team_id,
            "type": "teams",
            "attributes": {
                "name": "Updated Team Name",
                "description": "Original description",
                "created-at": "2024-01-10T10:00:00Z",
                "updated-at": "2024-01-20T10:00:00Z",
                "users-count": 3,
            },
        }
        mock_client.patch.return_value = {"data": response}

        team = api.update(team_id=team_id, name="Updated Team Name")

        # Verify API call
        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == f"/teams/{team_id}"

        # Verify payload
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["name"] == "Updated Team Name"

        # Verify returned team
        assert team.name == "Updated Team Name"

    def test_update_team_description(self, api, mock_client):
        """Test updating team description."""
        team_id = "team-update123"
        response = {
            "id": team_id,
            "type": "teams",
            "attributes": {
                "name": "Platform Team",
                "description": "Updated description",
                "created-at": "2024-01-10T10:00:00Z",
                "updated-at": "2024-01-20T10:00:00Z",
                "users-count": 3,
            },
        }
        mock_client.patch.return_value = {"data": response}

        team = api.update(team_id=team_id, description="Updated description")

        # Verify description in payload
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["description"] == "Updated description"

        # Verify returned team
        assert team.description == "Updated description"

    def test_update_team_multiple_fields(self, api, mock_client):
        """Test updating multiple team fields."""
        team_id = "team-update123"
        response = {
            "id": team_id,
            "type": "teams",
            "attributes": {
                "name": "New Name",
                "description": "New description",
                "created-at": "2024-01-10T10:00:00Z",
                "updated-at": "2024-01-20T10:00:00Z",
                "users-count": 3,
            },
        }
        mock_client.patch.return_value = {"data": response}

        team = api.update(
            team_id=team_id,
            name="New Name",
            description="New description",
        )

        # Verify both fields in payload
        call_args = mock_client.patch.call_args
        payload = call_args[1]["json_data"]
        assert payload["data"]["attributes"]["name"] == "New Name"
        assert payload["data"]["attributes"]["description"] == "New description"

        # Verify returned team
        assert team.name == "New Name"
        assert team.description == "New description"


class TestTeamDeletion:
    """Test team deletion operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create TeamsAPI instance with mock client."""
        return TeamsAPI(mock_client)

    def test_delete_team(self, api, mock_client):
        """Test deleting a team."""
        team_id = "team-delete123"
        mock_client.base_url = "https://app.terraform.io"
        mock_client.headers = {"Authorization": "Bearer token"}

        api.delete(team_id)

        # Verify API call
        mock_client.client.delete.assert_called_once()
        call_args = mock_client.client.delete.call_args
        assert f"/teams/{team_id}" in call_args[0][0]


class TestTeamMembers:
    """Test team member operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create TeamsAPI instance with mock client."""
        return TeamsAPI(mock_client)

    def test_list_team_members(self, api, mock_client):
        """Test listing team members."""
        team_id = "team-members123"
        members_data = [
            {
                "id": "user-1",
                "type": "users",
                "attributes": {
                    "username": "alice",
                },
            },
            {
                "id": "user-2",
                "type": "users",
                "attributes": {
                    "username": "bob",
                },
            },
        ]

        mock_client.paginate_with_meta.return_value = (iter(members_data), 2)

        members, total_count = api.list_members(team_id)

        # Verify pagination call
        mock_client.paginate_with_meta.assert_called_once()
        call_args = mock_client.paginate_with_meta.call_args
        assert call_args[0][0] == f"/teams/{team_id}/relationships/users"

        # Verify returned members
        assert len(members) == 2
        assert members[0]["id"] == "user-1"
        assert members[1]["id"] == "user-2"
        assert total_count == 2

    def test_add_team_member(self, api, mock_client):
        """Test adding a user to a team."""
        team_id = "team-members123"
        user_id = "user-new123"
        mock_client.post.return_value = {}

        api.add_member(team_id=team_id, user_id=user_id)

        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"/teams/{team_id}/relationships/users"

        # Verify payload
        payload = call_args[1]["json_data"]
        assert payload["data"][0]["type"] == "users"
        assert payload["data"][0]["id"] == user_id

    def test_remove_team_member(self, api, mock_client):
        """Test removing a user from a team."""
        team_id = "team-members123"
        user_id = "user-remove123"
        mock_client.base_url = "https://app.terraform.io"
        mock_response = MagicMock()
        mock_client.client.request.return_value = mock_response

        api.remove_member(team_id=team_id, user_id=user_id)

        # Verify API call
        mock_client.client.request.assert_called_once()
        call_args = mock_client.client.request.call_args
        assert call_args[0][0] == "DELETE"
        assert f"/teams/{team_id}/relationships/users" in call_args[0][1]

        # Verify payload contains user
        assert call_args[1]["json"]["data"][0]["id"] == user_id

        # Verify response was checked
        mock_response.raise_for_status.assert_called_once()


class TestTeamIntegration:
    """Integration tests for team operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TFC client."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """Create TeamsAPI instance with mock client."""
        return TeamsAPI(mock_client)

    def test_create_team_and_add_members(self, api, mock_client):
        """Test creating team and adding members."""
        org = "my-org"
        mock_client.get_organization.return_value = org

        # Mock create response
        create_response = {
            "id": "team-workflow123",
            "type": "teams",
            "attributes": {
                "name": "New Team",
                "description": "Test team",
                "created-at": "2024-01-20T10:00:00Z",
                "updated-at": "2024-01-20T10:00:00Z",
                "users-count": 0,
            },
        }
        mock_client.post.return_value = {"data": create_response}

        # Create team
        team = api.create(
            organization=org,
            name="New Team",
            description="Test team",
        )

        assert team.id == "team-workflow123"
        assert team.name == "New Team"

        # Mock add_member response
        mock_client.post.return_value = {}

        # Add members
        api.add_member(team_id=team.id, user_id="user-alice")
        api.add_member(team_id=team.id, user_id="user-bob")

        # Verify both add calls
        assert mock_client.post.call_count == 3  # 1 for create + 2 for adds

    def test_list_and_update_team(self, api, mock_client):
        """Test listing teams and updating one."""
        org = "my-org"
        mock_client.get_organization.return_value = org

        # Mock list response
        list_items = [
            {
                "id": "team-1",
                "type": "teams",
                "attributes": {
                    "name": "Platform Team",
                    "description": "Old description",
                    "created-at": "2024-01-10T10:00:00Z",
                    "updated-at": "2024-01-15T14:30:00Z",
                    "users-count": 5,
                },
            },
        ]
        mock_client.paginate_with_meta.return_value = (iter(list_items), 1)

        # List teams
        teams_iter, total = api.list_teams(organization=org)
        teams = list(teams_iter)

        assert len(teams) == 1
        assert teams[0].name == "Platform Team"

        # Mock update response
        update_response = {
            "id": "team-1",
            "type": "teams",
            "attributes": {
                "name": "Platform Team",
                "description": "New description",
                "created-at": "2024-01-10T10:00:00Z",
                "updated-at": "2024-01-20T10:00:00Z",
                "users-count": 5,
            },
        }
        mock_client.patch.return_value = {"data": update_response}

        # Update team
        updated_team = api.update(
            team_id=teams[0].id,
            description="New description",
        )

        assert updated_team.description == "New description"
