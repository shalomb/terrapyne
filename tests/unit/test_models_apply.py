"""Unit tests for Apply model."""

from terrapyne.models.apply import Apply


class TestApplyModel:
    """Test Apply model."""

    def test_apply_from_api_response(self):
        """Test creating Apply from API response."""
        api_response = {
            "id": "apply-123",
            "type": "applies",
            "attributes": {
                "status": "finished",
                "log-read-url": "https://logs.example.com/apply-123",
            },
        }

        apply_obj = Apply.from_api_response(api_response)

        assert apply_obj.id == "apply-123"
        assert apply_obj.status == "finished"
        assert apply_obj.log_read_url == "https://logs.example.com/apply-123"

    def test_apply_status_enum(self):
        """Test Apply status property."""
        api_response = {
            "id": "apply-456",
            "type": "applies",
            "attributes": {
                "status": "pending",
                "log-read-url": None,
            },
        }

        apply_obj = Apply.from_api_response(api_response)

        assert apply_obj.status == "pending"
