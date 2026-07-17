"""Tests for the core.device_registry parser."""

from pathlib import Path

import pytest

from engine.graph import DirectedGraph
from engine.parsers.device_registry import (
    DeviceRegistryFormatError,
    build_entity_device_edges,
    parse_device_registry,
)
from engine.parsers.entity_registry import (
    parse_entity_registry,
)


DEVICE_FIXTURE = (
    Path(__file__).parent / "fixtures" / "core.device_registry.sample"
)
ENTITY_FIXTURE = (
    Path(__file__).parent / "fixtures" / "core.entity_registry.sample"
)


def test_parse_all_valid_devices() -> None:
    result = parse_device_registry(DEVICE_FIXTURE)

    assert len(result.nodes) == 2
    assert len(result.edges) == 0
    assert len(result.warnings) == 2

    assert {node.node_id for node in result.nodes} == {
        "device:device_shelly",
        "device:device_sun",
    }


def test_device_name_and_metadata() -> None:
    result = parse_device_registry(DEVICE_FIXTURE)
    nodes = {node.node_id: node for node in result.nodes}

    shelly = nodes["device:device_shelly"]

    assert shelly.name == "Poolpump"
    assert shelly.metadata["manufacturer"] == "Shelly"
    assert shelly.metadata["model"] == "Shelly Plus 1PM"
    assert shelly.metadata["registry_id"] == "device_shelly"
    assert shelly.metadata["config_entries"] == ["entry_shelly"]


def test_build_entity_device_relations() -> None:
    entity_result = parse_entity_registry(ENTITY_FIXTURE)
    device_result = parse_device_registry(DEVICE_FIXTURE)

    relation_result = build_entity_device_edges(
        entity_result.nodes,
        device_result.nodes,
    )

    assert len(relation_result.edges) == 1
    assert len(relation_result.warnings) == 0

    edge = relation_result.edges[0]
    assert edge.source_node_id == "sensor.sun_next_dawn"
    assert edge.target_node_id == "device:device_sun"
    assert edge.relation_type.value == "belongs_to_device"


def test_results_can_populate_graph() -> None:
    entity_result = parse_entity_registry(ENTITY_FIXTURE)
    device_result = parse_device_registry(DEVICE_FIXTURE)
    relation_result = build_entity_device_edges(
        entity_result.nodes,
        device_result.nodes,
    )

    graph = DirectedGraph()
    graph.add_nodes(entity_result.nodes)
    graph.add_nodes(device_result.nodes)
    graph.add_edges(relation_result.edges)

    assert graph.node_count == 4
    assert graph.edge_count == 1
    assert graph.children("sensor.sun_next_dawn") == frozenset(
        {"device:device_sun"}
    )
    assert graph.parents("device:device_sun") == frozenset(
        {"sensor.sun_next_dawn"}
    )


def test_missing_device_becomes_warning() -> None:
    entity_result = parse_entity_registry(ENTITY_FIXTURE)

    relation_result = build_entity_device_edges(
        entity_result.nodes,
        [],
    )

    assert len(relation_result.edges) == 0
    assert len(relation_result.warnings) == 1


def test_reject_wrong_storage_key(tmp_path: Path) -> None:
    bad_file = tmp_path / "wrong.json"
    bad_file.write_text(
        '{"key":"core.entity_registry","data":{"devices":[]}}',
        encoding="utf-8",
    )

    with pytest.raises(DeviceRegistryFormatError):
        parse_device_registry(bad_file)
