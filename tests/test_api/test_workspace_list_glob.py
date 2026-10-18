"""Workspace list: glob patterns use coarse server search + client fnmatch."""

from unittest.mock import MagicMock

from terrapyne.api.workspaces import WorkspaceAPI


def _item(name):
    return {"id": f"ws-{name}", "type": "workspaces", "attributes": {"name": name}}


def _api(names):
    client = MagicMock()
    client.get_organization.return_value = "org"
    it = MagicMock()
    it.__iter__.return_value = iter([_item(n) for n in names])
    it.included = []
    client.paginate.return_value = (it, len(names))
    return WorkspaceAPI(client), client


def test_middle_wildcard_uses_longest_literal_and_fnmatch():
    api, client = _api(["tec-man-a-dev-10345-x", "tec-man-a-prod-10345-x"])
    items, total = api.list(search="tec-man-*-dev-10345-*")
    assert [w.name for w in items] == ["tec-man-a-dev-10345-x"]
    params = client.paginate.call_args.kwargs["params"]
    assert params["search[name]"] == "-dev-10345-"
    assert "search[wildcard-name]" not in params
    assert total is None


def test_plain_search_unchanged():
    api, client = _api(["a"])
    api.list(search="abc")
    assert client.paginate.call_args.kwargs["params"]["search[name]"] == "abc"
