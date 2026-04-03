import pytest
from terrapyne.core.backend import RemoteBackend, detect_backend


@pytest.mark.fast
@pytest.mark.unit
def test_detect_backend_with_name(fixtures_dir):
    tf_file = fixtures_dir / "terraform_tf" / "remote_backend.tf"
    result = detect_backend(path=tf_file.parent)
    assert isinstance(result, RemoteBackend)
    assert result.organization == "my-org"
    assert result.workspace_name == "my-workspace"


@pytest.mark.fast
@pytest.mark.unit
def test_detect_backend_with_prefix(fixtures_dir):
    tf_file = fixtures_dir / "terraform_tf" / "remote_backend_prefix.tf"
    result = detect_backend(path=tf_file.parent)
    assert isinstance(result, RemoteBackend)
    assert result.organization == "my-org"
    assert result.workspace_prefix == "my-app-"
