from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node, RelationType
from engine.parsers.automations import (
    parse_automation_relations,
)


FIXTURE = Path(__file__).parent / "fixtures" / "automations.sample.yaml"


def _nodes() -> list[Node]:
    ids = [
        "automation.test_automation",
        "binary_sensor.motion",
        "input_boolean.enable_test",
        "sensor.temperature",
        "input_number.target_temperature",
        "input_select.mode",
        "light.test",
        "input_number.brightness",
        "script.notify_family",
        "input_boolean.extra",
        "switch.one",
        "switch.two",
    ]

    nodes = [
        Node(entity_id, "entity", metadata={"platform": entity_id.split(".")[0]})
        for entity_id in ids
    ]

    nodes[0] = Node(
        "automation.test_automation",
        "entity",
        metadata={"platform": "automation", "unique_id": "1001"},
    )
    return nodes


def test_trigger_and_condition_sources_point_to_automation() -> None:
    result = parse_automation_relations(FIXTURE, _nodes())
    pairs = {
        (edge.source_node_id, edge.target_node_id, edge.relation_type)
        for edge in result.edges
    }

    assert (
        "binary_sensor.motion",
        "automation.test_automation",
        RelationType.TRIGGERS,
    ) in pairs
    assert (
        "input_boolean.enable_test",
        "automation.test_automation",
        RelationType.TRIGGERS,
    ) in pairs
    assert (
        "sensor.temperature",
        "automation.test_automation",
        RelationType.READS,
    ) in pairs
    assert (
        "input_number.target_temperature",
        "automation.test_automation",
        RelationType.READS,
    ) in pairs
    assert (
        "input_select.mode",
        "automation.test_automation",
        RelationType.READS,
    ) in pairs


def test_actions_create_outgoing_and_input_relations() -> None:
    result = parse_automation_relations(FIXTURE, _nodes())
    pairs = {
        (edge.source_node_id, edge.target_node_id, edge.relation_type)
        for edge in result.edges
    }

    assert (
        "automation.test_automation",
        "light.test",
        RelationType.WRITES,
    ) in pairs
    assert (
        "automation.test_automation",
        "script.notify_family",
        RelationType.CALLS_SCRIPT,
    ) in pairs
    assert (
        "input_number.brightness",
        "automation.test_automation",
        RelationType.READS,
    ) in pairs
    assert (
        "automation.test_automation",
        "switch.one",
        RelationType.WRITES,
    ) in pairs
    assert (
        "automation.test_automation",
        "switch.two",
        RelationType.WRITES,
    ) in pairs


def test_service_names_are_not_entity_relations() -> None:
    result = parse_automation_relations(FIXTURE, _nodes())

    assert all(
        edge.source_node_id not in {
            "light.turn_on",
            "switch.turn_on",
        }
        and edge.target_node_id not in {
            "light.turn_on",
            "switch.turn_on",
        }
        for edge in result.edges
    )


def test_nested_choose_condition_is_read() -> None:
    result = parse_automation_relations(FIXTURE, _nodes())

    assert any(
        edge.source_node_id == "input_boolean.extra"
        and edge.target_node_id == "automation.test_automation"
        and edge.relation_type == RelationType.READS
        for edge in result.edges
    )


def test_relations_populate_graph() -> None:
    nodes = _nodes()
    result = parse_automation_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert "automation.test_automation" in graph.children(
        "binary_sensor.motion"
    )
    assert "light.test" in graph.children(
        "automation.test_automation"
    )
