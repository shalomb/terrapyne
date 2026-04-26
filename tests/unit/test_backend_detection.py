import shutil

import pytest

from terrapyne.core.backend import RemoteBackend, detect_backend


@pytest.mark.fast
@pytest.mark.unit
def test_detect_backend_with_name(tmp_path, fixtures_dir):
    shutil.copy(fixtures_dir / "terraform_tf" / "remote_backend.tf", tmp_path)
    result = detect_backend(path=tmp_path)
    assert isinstance(result, RemoteBackend)
    assert result.organization == "my-org"
    assert result.workspace_name == "my-workspace"


@pytest.mark.fast
@pytest.mark.unit
def test_detect_backend_with_prefix(tmp_path, fixtures_dir):
    shutil.copy(fixtures_dir / "terraform_tf" / "remote_backend_prefix.tf", tmp_path)
    result = detect_backend(path=tmp_path)
    assert isinstance(result, RemoteBackend)
    assert result.organization == "my-org"
    assert result.workspace_prefix == "my-app-"


@pytest.mark.fast
@pytest.mark.unit
def test_detect_cloud_block_with_name(tmp_path, fixtures_dir):
    shutil.copy(fixtures_dir / "terraform_tf" / "cloud_block_name.tf", tmp_path)
    result = detect_backend(path=tmp_path)
    assert isinstance(result, RemoteBackend)
    assert result.organization == "my-org"
    assert result.workspace_name == "my-workspace"


@pytest.mark.fast
@pytest.mark.unit
def test_detect_cloud_block_with_prefix(tmp_path, fixtures_dir):
    shutil.copy(fixtures_dir / "terraform_tf" / "cloud_block_prefix.tf", tmp_path)
    result = detect_backend(path=tmp_path)
    assert isinstance(result, RemoteBackend)
    assert result.organization == "my-org"
    assert result.workspace_prefix == "my-app-"


@pytest.mark.fast
@pytest.mark.unit
def test_detect_cloud_block_with_tags(tmp_path, fixtures_dir):
    shutil.copy(fixtures_dir / "terraform_tf" / "cloud_block_tags.tf", tmp_path)
    result = detect_backend(path=tmp_path)
    assert isinstance(result, RemoteBackend)
    assert result.organization == "my-org"
    assert result.workspace_name is None
    assert result.workspace_prefix is None


@pytest.mark.fast
@pytest.mark.unit
def test_detect_cloud_block_with_hostname(tmp_path, fixtures_dir):
    shutil.copy(fixtures_dir / "terraform_tf" / "cloud_block_hostname.tf", tmp_path)
    result = detect_backend(path=tmp_path)
    assert isinstance(result, RemoteBackend)
    assert result.hostname == "tfe.example.com"
    assert result.organization == "my-org"
    assert result.workspace_name == "my-workspace"
