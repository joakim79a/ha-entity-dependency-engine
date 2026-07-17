"""Tests for the core.config_entries parser."""

from pathlib import Path

import pytest

from engine.graph import DirectedGraph
from engine.parsers.config_entries import (
    ConfigEntriesFormatError,
    build_device_config_entry_edges,
    build_entity_config_entry_edges,
    parse_config_entries,
)
from engine.parsers.device_registry import (
    parse_device_registry,
)
from engine.parsers.entity_registry import (
    parse_entity_registry,
)


BASE = Path(__file__).parent / "fixtures"
CONFIG_FIXTURE = BASE / "core.config_entries.sample"
DEVICE_FIXTURE = BASE / "core.device_registry.sample"
ENTITY_FIXTURE = BASE / "core.entity_registry.sample"


def test_parse_all_valid_config_entries() -> None:
    result = parse_config_entries(CONFIG_FIXTURE)

    assert len(result.nodes) == 3
    assert len(result.edges) == 0
    assert len(result.warnings) == 2

    assert {node.node_id for node in result.nodes} == {
        "config_entry:entry_sun",
        "config_entry:entry_price",
        "config_entry:entry_shelly",
    }


def test_config_entry_name_and_metadata() -> None:
    result = parse_config_entries(CONFIG_FIXTURE)
    nodes = {node.node_id: node for node in result.nodes}

    tibber = nodes["config_entry:entry_price"]

    assert tibber.name == "Pulse Energy"
    assert tibber.metadata["domain"] == "tibber"
    assert tibber.metadata["entry_id"] == "entry_price"
    assert tibber.metadata["source"] == "user"


def test_build_entity_config_entry_relations() -> None:
    entity_result = parse_entity_registry(ENTITY_FIXTURE)
    config_result = parse_config_entries(CONFIG_FIXTURE)

    relation_result = build_entity_config_entry_edges(
        entity_result.nodes,
        config_result.nodes,
    )

    assert len(relation_result.edges) == 2
    assert len(relation_result.warnings) == 0


def test_build_device_config_entry_relations() -> None:
    device_result = parse_device_registry(DEVICE_FIXTURE)
    config_result = parse_config_entries(CONFIG_FIXTURE)

    relation_result = build_device_config_entry_edges(
        device_result.nodes,
        config_result.nodes,
    )

    assert len(relation_result.edges) == 2
    assert len(relation_result.warnings) == 0


def test_all_results_populate_graph() -> None:
    entity_result = parse_entity_registry(ENTITY_FIXTURE)
    device_result = parse_device_registry(DEVICE_FIXTURE)
    config_result = parse_config_entries(CONFIG_FIXTURE)

    entity_config = build_entity_config_entry_edges(
        entity_result.nodes,
        config_result.nodes,
    )
    device_config = build_device_config_entry_edges(
        device_result.nodes,
        config_result.nodes,
    )

    graph = DirectedGraph()
    graph.add_nodes(entity_result.nodes)
    graph.add_nodes(device_result.nodes)
    graph.add_nodes(config_result.nodes)
    graph.add_edges(entity_config.edges)
    graph.add_edges(device_config.edges)

    assert graph.node_count == 7
    assert graph.edge_count == 4

    assert graph.children("sensor.pulse_elpris") == frozenset(
        {"config_entry:entry_price"}
    )
    assert graph.children("device:device_sun") == frozenset(
        {"config_entry:entry_sun"}
    )


def test_missing_config_entry_becomes_warning() -> None:
    entity_result = parse_entity_registry(ENTITY_FIXTURE)

    relation_result = build_entity_config_entry_edges(
        entity_result.nodes,
        [],
    )

    assert len(relation_result.edges) == 0
    assert len(relation_result.warnings) == 2


def test_reject_wrong_storage_key(tmp_path: Path) -> None:
    bad_file = tmp_path / "wrong.json"
    bad_file.write_text(
        '{"key":"core.device_registry","data":{"entries":[]}}',
        encoding="utf-8",
    )

    with pytest.raises(ConfigEntriesFormatError):
        parse_config_entries(bad_file)
