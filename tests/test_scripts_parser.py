from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node, RelationType
from engine.parsers.scripts import parse_script_relations


FIXTURE = Path(__file__).parent / "fixtures" / "scripts.sample.yaml"


def _nodes() -> list[Node]:
    ids = [
        "script.test_script",
        "script.child_script",
        "light.test",
        "input_number.brightness",
        "input_boolean.enable_extra",
        "switch.extra",
    ]

    return [
        Node(
            entity_id,
            "entity",
            metadata={"platform": entity_id.split(".")[0]},
        )
        for entity_id in ids
    ]


def test_script_reads_helpers_and_templates() -> None:
    result = parse_script_relations(FIXTURE, _nodes())

    pairs = {
        (edge.source_node_id, edge.target_node_id, edge.relation_type)
        for edge in result.edges
    }

    assert (
        "input_number.brightness",
        "script.test_script",
        RelationType.READS,
    ) in pairs

    assert (
        "input_boolean.enable_extra",
        "script.test_script",
        RelationType.READS,
    ) in pairs


def test_script_writes_targets_and_calls_scripts() -> None:
    result = parse_script_relations(FIXTURE, _nodes())

    pairs = {
        (edge.source_node_id, edge.target_node_id, edge.relation_type)
        for edge in result.edges
    }

    assert (
        "script.test_script",
        "light.test",
        RelationType.WRITES,
    ) in pairs

    assert (
        "script.test_script",
        "script.child_script",
        RelationType.CALLS_SCRIPT,
    ) in pairs

    assert (
        "script.test_script",
        "switch.extra",
        RelationType.WRITES,
    ) in pairs


def test_service_names_are_not_entity_relations() -> None:
    result = parse_script_relations(FIXTURE, _nodes())

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


def test_relations_populate_graph() -> None:
    nodes = _nodes()
    result = parse_script_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert "script.test_script" in graph.children(
        "input_number.brightness"
    )
    assert "light.test" in graph.children("script.test_script")
