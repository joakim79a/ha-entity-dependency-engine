"""Tests for the graph core."""

from engine.graph import DirectedGraph
from engine.model import (
    Confidence,
    Edge,
    Node,
    RelationType,
)


def build_sample_graph() -> DirectedGraph:
    graph = DirectedGraph()

    graph.add_nodes(
        [
            Node("sensor.raw", "entity", "Raw sensor"),
            Node("sensor.template", "entity", "Template sensor"),
            Node("automation.control", "automation", "Control"),
            Node("switch.output", "entity", "Output"),
        ]
    )

    graph.add_edges(
        [
            Edge(
                "sensor.raw",
                "sensor.template",
                RelationType.READS,
                source_parser="test",
            ),
            Edge(
                "sensor.template",
                "automation.control",
                RelationType.TRIGGERS,
                source_parser="test",
            ),
            Edge(
                "automation.control",
                "switch.output",
                RelationType.WRITES,
                source_parser="test",
                confidence=Confidence.CERTAIN,
            ),
        ]
    )

    return graph


def test_direct_relations() -> None:
    graph = build_sample_graph()

    assert graph.children("sensor.raw") == frozenset({"sensor.template"})
    assert graph.parents("sensor.template") == frozenset({"sensor.raw"})


def test_recursive_relations() -> None:
    graph = build_sample_graph()

    assert graph.descendants("sensor.raw") == {
        "sensor.template": 1,
        "automation.control": 2,
        "switch.output": 3,
    }

    assert graph.ancestors("switch.output") == {
        "automation.control": 1,
        "sensor.template": 2,
        "sensor.raw": 3,
    }


def test_shortest_path() -> None:
    graph = build_sample_graph()

    assert graph.shortest_path("sensor.raw", "switch.output") == [
        "sensor.raw",
        "sensor.template",
        "automation.control",
        "switch.output",
    ]


def test_cycle_safe_traversal() -> None:
    graph = build_sample_graph()

    graph.add_edge(
        Edge(
            "switch.output",
            "sensor.raw",
            RelationType.REFERENCES,
            source_parser="test",
        )
    )

    descendants = graph.descendants("sensor.raw")

    assert descendants == {
        "sensor.template": 1,
        "automation.control": 2,
        "switch.output": 3,
    }


def test_duplicate_edge_is_ignored() -> None:
    graph = build_sample_graph()
    edge = Edge(
        "sensor.raw",
        "sensor.template",
        RelationType.READS,
        source_parser="test",
    )

    original_count = graph.edge_count
    graph.add_edge(edge)

    assert graph.edge_count == original_count


def test_missing_nodes_can_be_preserved() -> None:
    graph = DirectedGraph()

    graph.add_edge(
        Edge(
            "sensor.missing_source",
            "sensor.missing_target",
            RelationType.REFERENCES,
            source_parser="test",
            confidence=Confidence.PROBABLE,
        ),
        create_missing_nodes=True,
    )

    assert graph.get_node("sensor.missing_source") is not None
    assert graph.get_node("sensor.missing_target") is not None
    assert graph.edge_count == 1
