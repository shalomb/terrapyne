import pytest

from terrapyne.core.credentials import TerraformCredentials


@pytest.mark.fast
@pytest.mark.unit
def test_load_credentials_public_tfc(fixtures_dir):
    tfrc = fixtures_dir / "credentials" / "credentials.tfrc.json"
    creds = TerraformCredentials.load(tfrc_path=tfrc)
    assert creds.host == "app.terraform.io"
    assert creds.token == "test-token-123"


@pytest.mark.fast
@pytest.mark.unit
def test_load_credentials_private_tfe(fixtures_dir):
    tfrc = fixtures_dir / "credentials" / "credentials.tfrc.json"
    creds = TerraformCredentials.load(
        host="tfe.example.com",
        tfrc_path=tfrc,
    )
    assert creds.token == "test-token-456"


@pytest.mark.fast
@pytest.mark.unit
def test_load_credentials_missing_host(fixtures_dir):
    tfrc = fixtures_dir / "credentials" / "credentials.tfrc.json"
    with pytest.raises(KeyError, match="No credentials"):
        TerraformCredentials.load(
            host="missing.example.com",
            tfrc_path=tfrc,
        )
