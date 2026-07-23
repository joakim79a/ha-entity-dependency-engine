"""Static contract guards for the Home Assistant WebSocket API."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "entity_dependency_engine"


def _source(filename: str) -> str:
    return (INTEGRATION / filename).read_text(encoding="utf-8")


def test_websocket_command_names_are_stable() -> None:
    tree = ast.parse(_source("const.py"))
    values: dict[str, object] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            values[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue

    assert (
        values["WS_SEARCH_ENTITIES"]
        == "entity_dependency_engine/search_entities"
    )
    assert values["WS_GET_GRAPH"] == "entity_dependency_engine/get_graph"
    assert (
        values["WS_EXPAND_NODE"]
        == "entity_dependency_engine/expand_node"
    )


def test_websocket_endpoints_are_admin_only_and_async() -> None:
    source = _source("websocket.py")

    assert "async def websocket_search_entities(" in source
    assert "async def websocket_get_graph(" in source
    assert "async def websocket_expand_node(" in source
    assert source.count("@websocket_api.require_admin") == 3
    assert source.count("@websocket_api.async_response") == 3
    assert "vol.Required(\"entity_id\"): cv.entity_id" in source
    assert "vol.In(VALID_SCOPES)" in source
    assert "vol.Range(min=1, max=ABSOLUTE_MAX_NODES)" in source


def test_integration_registers_websocket_without_changing_report_action() -> None:
    source = _source("__init__.py")

    assert "async_register_websocket_commands(hass)" in source
    assert "SERVICE_GENERATE_REPORT" in source
    assert "generate_report(" in source
    assert "ReportSnapshot.from_generated_report(result)" in source


def test_expand_node_websocket_contract_is_bounded() -> None:
    source = _source("websocket.py")

    assert 'vol.Required("root_id"): cv.entity_id' in source
    assert 'vol.Required("node_id"): cv.string' in source
    assert 'vol.Required("direction"): vol.In(' in source
    assert 'vol.Required("visible_node_ids"): vol.All(' in source
    assert '[cv.string]' in source
    assert "vol.Length(min=1, max=ABSOLUTE_MAX_NODES)" in source
    assert "expand_panel_graph" in source
    assert "websocket_expand_node" in source
