"""Tests for state diff and resource extraction."""

from terrapyne.core.state_diff import (
    StateDiff,
    StateResourceInstance,
    diff_state_resources,
    extract_rows,
    format_diff_unified,
    parse_state_resources,
    resolve_field,
)
from terrapyne.models.state_version import StateVersion, StateVersionOutput


SAMPLE_STATE = {
    "resources": [
        {
            "module": "module.vpc",
            "mode": "managed",
            "type": "aws_subnet",
            "name": "private",
            "instances": [
                {"index_key": 0, "attributes": {"id": "subnet-aaa", "arn": "arn:aws:ec2:us-east-1:123:subnet/subnet-aaa", "tags": {"Name": "private-0"}, "availability_zone": "us-east-1a"}},
                {"index_key": 1, "attributes": {"id": "subnet-bbb", "arn": "arn:aws:ec2:us-east-1:123:subnet/subnet-bbb", "tags": {"Name": "private-1"}, "availability_zone": "us-east-1b"}},
            ],
        },
        {
            "mode": "managed",
            "type": "aws_instance",
            "name": "web",
            "instances": [
                {"attributes": {"id": "i-12345", "arn": "arn:aws:ec2:us-east-1:123:instance/i-12345", "tags": {"Name": "web-server"}, "private_ip": "10.0.1.5"}},
            ],
        },
        {
            "mode": "data",
            "type": "aws_ami",
            "name": "ubuntu",
            "instances": [
                {"attributes": {"id": "ami-abc123", "name": "ubuntu-22.04"}},
            ],
        },
    ]
}


class TestParseStateResources:
    def test_parse_all_managed(self):
        result = parse_state_resources(SAMPLE_STATE)
        assert len(result) == 3  # 2 subnets + 1 instance (data source excluded)

    def test_filter_by_type(self):
        result = parse_state_resources(SAMPLE_STATE, types={"aws_instance"})
        assert len(result) == 1
        assert result[0].resource_type == "aws_instance"

    def test_filter_by_mode_data(self):
        result = parse_state_resources(SAMPLE_STATE, mode="data")
        assert len(result) == 1
        assert result[0].resource_type == "aws_ami"

    def test_filter_by_module(self):
        result = parse_state_resources(SAMPLE_STATE, module_pattern="module.vpc")
        assert len(result) == 2
        assert all(i.module == "module.vpc" for i in result)

    def test_root_resource_has_no_module(self):
        result = parse_state_resources(SAMPLE_STATE, types={"aws_instance"})
        assert result[0].module is None


class TestStateResourceInstance:
    def test_address_with_module_and_index(self):
        inst = StateResourceInstance(
            resource_type="aws_subnet", resource_name="private",
            module="module.vpc", index_key=0, attributes={},
        )
        assert inst.address == "module.vpc.aws_subnet.private[0]"

    def test_address_root_no_index(self):
        inst = StateResourceInstance(
            resource_type="aws_instance", resource_name="web",
            module=None, index_key=None, attributes={},
        )
        assert inst.address == "aws_instance.web"

    def test_get_field_dotted_path(self):
        inst = StateResourceInstance(
            resource_type="aws_instance", resource_name="web",
            module=None, index_key=None,
            attributes={"tags": {"Name": "my-server"}, "id": "i-123"},
        )
        assert inst.get_field("tags.Name") == "my-server"
        assert inst.get_field("id") == "i-123"
        assert inst.get_field("nonexistent.path") is None


class TestResolveField:
    def test_type_field(self):
        inst = StateResourceInstance("aws_instance", "web", None, None, {})
        assert resolve_field(inst, "type") == "aws_instance"

    def test_address_field(self):
        inst = StateResourceInstance("aws_instance", "web", "module.app", None, {})
        assert resolve_field(inst, "address") == "module.app.aws_instance.web"

    def test_name_uses_alias_fallback(self):
        inst = StateResourceInstance("aws_instance", "web", None, None, {"tags": {"Name": "my-web"}})
        assert resolve_field(inst, "name") == "my-web"

    def test_direct_dotted_path(self):
        inst = StateResourceInstance("aws_instance", "web", None, None, {"tags": {"Environment": "prod"}})
        assert resolve_field(inst, "tags.Environment") == "prod"


class TestDiffStateResources:
    def test_all_added_when_old_empty(self):
        new = parse_state_resources(SAMPLE_STATE)
        result = diff_state_resources([], new)
        assert len(result.added) == 3
        assert len(result.removed) == 0

    def test_all_removed_when_new_empty(self):
        old = parse_state_resources(SAMPLE_STATE)
        result = diff_state_resources(old, [])
        assert len(result.removed) == 3
        assert len(result.added) == 0

    def test_identical_states_no_diff(self):
        instances = parse_state_resources(SAMPLE_STATE)
        result = diff_state_resources(instances, instances)
        assert len(result.added) == 0
        assert len(result.removed) == 0

    def test_detects_added_resource(self):
        old = parse_state_resources(SAMPLE_STATE, types={"aws_subnet"})
        new = parse_state_resources(SAMPLE_STATE)  # includes aws_instance too
        result = diff_state_resources(old, new)
        assert len(result.added) == 1
        assert result.added[0].resource_type == "aws_instance"


class TestExtractRows:
    def test_extracts_requested_fields(self):
        instances = parse_state_resources(SAMPLE_STATE, types={"aws_instance"})
        rows = extract_rows(instances, ["type", "id", "tags.Name"])
        assert len(rows) == 1
        assert rows[0]["type"] == "aws_instance"
        assert rows[0]["id"] == "i-12345"
        assert rows[0]["tags.Name"] == "web-server"


class TestFormatDiffUnified:
    def test_no_differences(self):
        instances = parse_state_resources(SAMPLE_STATE)
        output = format_diff_unified(instances, instances, ["type", "id"])
        assert "No differences" in output

    def test_produces_diff_output(self):
        old = parse_state_resources(SAMPLE_STATE, types={"aws_subnet"})
        new = parse_state_resources(SAMPLE_STATE)
        output = format_diff_unified(old, new, ["type", "id"])
        assert "aws_instance" in output


class TestStateVersionModel:
    def test_from_api_response(self):
        data = {
            "id": "sv-abc123",
            "attributes": {
                "serial": 42,
                "created-at": "2025-06-15T10:30:00Z",
                "status": "finalized",
                "hosted-state-download-url": "https://archivist.terraform.io/v1/object/abc",
                "resource-count": 15,
                "providers-count": 3,
                "resources-processed": True,
            },
            "relationships": {
                "run": {"data": {"id": "run-xyz789", "type": "runs"}},
            },
        }
        sv = StateVersion.from_api_response(data)
        assert sv.id == "sv-abc123"
        assert sv.serial == 42
        assert sv.status == "finalized"
        assert sv.resource_count == 15
        assert sv.run_id == "run-xyz789"
        assert sv.download_url == "https://archivist.terraform.io/v1/object/abc"

    def test_from_api_response_minimal(self):
        data = {"id": "sv-min", "attributes": {}, "relationships": {}}
        sv = StateVersion.from_api_response(data)
        assert sv.id == "sv-min"
        assert sv.serial == 0
        assert sv.run_id is None


class TestStateVersionOutput:
    def test_basic(self):
        o = StateVersionOutput(name="vpc_id", value="vpc-123", type="string", sensitive=False)
        assert o.name == "vpc_id"
        assert o.value == "vpc-123"


class TestAddressWithStringIndex:
    def test_string_index_key(self):
        inst = StateResourceInstance(
            resource_type="aws_route53_record",
            resource_name="this",
            module="module.dns",
            index_key="app.example.com",
            attributes={},
        )
        assert inst.address == 'module.dns.aws_route53_record.this[app.example.com]'


class TestResolveFieldEdgeCases:
    def test_unknown_field_returns_empty(self):
        inst = StateResourceInstance("aws_instance", "web", None, None, {})
        assert resolve_field(inst, "nonexistent") == ""

    def test_module_field_root(self):
        inst = StateResourceInstance("aws_instance", "web", None, None, {})
        assert resolve_field(inst, "module") == "(root)"

    def test_module_field_with_module(self):
        inst = StateResourceInstance("aws_instance", "web", "module.app", None, {})
        assert resolve_field(inst, "module") == "module.app"

    def test_name_falls_back_to_id_when_no_tags(self):
        inst = StateResourceInstance("aws_instance", "web", None, None, {"id": "i-fallback"})
        # "name" alias chain: tags.Name -> name -> identifier -> id
        assert resolve_field(inst, "name") == "i-fallback"


class TestParseStateResourcesEdgeCases:
    def test_empty_state(self):
        assert parse_state_resources({}) == []

    def test_no_instances(self):
        state = {"resources": [{"mode": "managed", "type": "aws_instance", "name": "x", "instances": []}]}
        assert parse_state_resources(state) == []

    def test_mode_none_returns_all(self):
        result = parse_state_resources(SAMPLE_STATE, mode=None)
        assert len(result) == 4  # 2 subnets + 1 instance + 1 data source
