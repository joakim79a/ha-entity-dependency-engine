from pathlib import Path
import pytest

from engine.graph import DirectedGraph
from engine.parsers.entity_registry import (
    EntityRegistryFormatError,
    parse_entity_registry,
)

FIXTURE = Path(__file__).parent / "fixtures" / "core.entity_registry.sample"

def test_parse_all_valid_entities() -> None:
    result = parse_entity_registry(FIXTURE)
    assert len(result.nodes) == 2
    assert len(result.edges) == 0
    assert len(result.warnings) == 2
    assert {node.node_id for node in result.nodes} == {
        "sensor.sun_next_dawn",
        "sensor.pulse_elpris",
    }

def test_name_priority_and_metadata() -> None:
    result = parse_entity_registry(FIXTURE)
    nodes = {node.node_id: node for node in result.nodes}
    sun = nodes["sensor.sun_next_dawn"]
    price = nodes["sensor.pulse_elpris"]

    assert sun.name == "Nästa gryning"
    assert price.name == "Pulse elpris"
    assert sun.metadata["domain"] == "sensor"
    assert sun.metadata["platform"] == "sun"
    assert sun.metadata["device_id"] == "device_sun"
    assert sun.metadata["config_entry_id"] == "entry_sun"
    assert price.metadata["area_id"] == "energy"
    assert price.metadata["labels"] == ["critical"]
    assert price.metadata["unit_of_measurement"] == "SEK/kWh"

def test_parser_result_can_populate_graph() -> None:
    result = parse_entity_registry(FIXTURE)
    graph = DirectedGraph()
    graph.add_nodes(result.nodes)
    assert graph.node_count == 2
    assert graph.get_node("sensor.pulse_elpris") is not None

def test_reject_wrong_storage_key(tmp_path: Path) -> None:
    bad_file = tmp_path / "wrong.json"
    bad_file.write_text(
        '{"key":"core.device_registry","data":{"entities":[]}}',
        encoding="utf-8",
    )
    with pytest.raises(EntityRegistryFormatError):
        parse_entity_registry(bad_file)

def test_reject_missing_entities_list(tmp_path: Path) -> None:
    bad_file = tmp_path / "wrong.json"
    bad_file.write_text(
        '{"key":"core.entity_registry","data":{}}',
        encoding="utf-8",
    )
    with pytest.raises(EntityRegistryFormatError):
        parse_entity_registry(bad_file)
