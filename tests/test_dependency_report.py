from engine.graph import DirectedGraph
from engine.model import (
    Confidence,
    Edge,
    Node,
    RelationType,
)
from engine.reports.dependency import (
    build_dependency_report,
)
from engine.reports.text import (
    format_dependency_report,
)


def _graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_nodes([
        Node("sensor.raw", "entity", "Raw"),
        Node("sensor.template", "entity", "Template"),
        Node("automation.control", "automation", "Control"),
        Node("switch.output", "entity", "Output"),
        Node("device:abc", "device", "Device"),
        Node("sensor.deleted", "unknown_entity"),
    ])

    graph.add_edges([
        Edge(
            "sensor.raw",
            "sensor.template",
            RelationType.SOURCE_OF,
            "test",
        ),
        Edge(
            "sensor.template",
            "automation.control",
            RelationType.TRIGGERS,
            "test",
        ),
        Edge(
            "automation.control",
            "switch.output",
            RelationType.WRITES,
            "test",
        ),
        Edge(
            "sensor.raw",
            "device:abc",
            RelationType.BELONGS_TO_DEVICE,
            "test",
        ),
        Edge(
            "sensor.deleted",
            "sensor.template",
            RelationType.SOURCE_OF,
            "test",
            confidence=Confidence.PROBABLE,
        ),
    ])

    return graph


def test_report_contains_recursive_relations() -> None:
    report = build_dependency_report(_graph(), "sensor.raw")

    assert {item.node.node_id for item in report.direct_children} == {
        "sensor.template",
        "device:abc",
    }
    assert {item.node.node_id for item in report.descendants} == {
        "sensor.template",
        "automation.control",
        "switch.output",
        "device:abc",
    }


def test_report_can_exclude_structural_relations() -> None:
    report = build_dependency_report(
        _graph(),
        "sensor.raw",
        include_structural=False,
    )

    assert {item.node.node_id for item in report.direct_children} == {
        "sensor.template"
    }


def test_report_detects_broken_references() -> None:
    report = build_dependency_report(
        _graph(),
        "sensor.template",
    )

    assert {item.node.node_id for item in report.broken_references} == {
        "sensor.deleted"
    }


def test_text_formatter_contains_relation_metadata() -> None:
    report = build_dependency_report(
        _graph(),
        "sensor.raw",
        include_structural=False,
    )

    text = format_dependency_report(report)

    assert "sensor.template" in text
    assert "source_of | test | certain" in text
    assert "Summary:" in text
