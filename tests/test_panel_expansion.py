"""Tests for one-step panel graph expansion."""

from __future__ import annotations

import pytest

from engine.graph import DirectedGraph
from engine.model import Edge, Node, RelationType
from engine.panel_expansion import expand_panel_graph


def _graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node("sensor.parent", "entity", "Parent"),
            Node("sensor.root", "entity", "Root"),
            Node("automation.child", "automation", "Child"),
            Node("script.grandchild", "script", "Grandchild"),
            Node("sensor.shared_parent", "entity", "Shared parent"),
            Node("device-1", "device", "Structural device"),
        ]
    )
    graph.add_edges(
        [
            Edge(
                "sensor.parent",
                "sensor.root",
                RelationType.READS,
                source_parser="test",
            ),
            Edge(
                "sensor.root",
                "automation.child",
                RelationType.TRIGGERS,
                source_parser="test",
            ),
            Edge(
                "automation.child",
                "script.grandchild",
                RelationType.CALLS_SCRIPT,
                source_parser="test",
            ),
            Edge(
                "sensor.shared_parent",
                "automation.child",
                RelationType.READS,
                source_parser="test",
            ),
            Edge(
                "sensor.root",
                "device-1",
                RelationType.BELONGS_TO_DEVICE,
                source_parser="test",
            ),
        ]
    )
    return graph


def _visible() -> list[str]:
    return ["sensor.root", "sensor.parent", "automation.child"]


def test_expand_children_returns_merged_graph_relative_to_original_root() -> None:
    payload = expand_panel_graph(
        _graph(),
        "sensor.root",
        "automation.child",
        direction="children",
        visible_node_ids=_visible(),
    )

    assert payload["root_id"] == "sensor.root"
    assert payload["scope"] == "expanded"
    assert payload["expansion"] == {
        "node_id": "automation.child",
        "direction": "children",
        "added_node_ids": ["script.grandchild"],
        "already_loaded": False,
        "omitted_node_count": 0,
    }
    assert [node["id"] for node in payload["nodes"]] == [
        "sensor.root",
        "sensor.parent",
        "automation.child",
        "script.grandchild",
    ]
    grandchild = next(
        node for node in payload["nodes"]
        if node["id"] == "script.grandchild"
    )
    assert "descendant" in grandchild["roles"]
    assert payload["statistics"]["node_count"] == 4
    assert payload["statistics"]["edge_count"] == 3


def test_expand_parents_can_add_cross_link_without_changing_root() -> None:
    payload = expand_panel_graph(
        _graph(),
        "sensor.root",
        "automation.child",
        direction="parents",
        visible_node_ids=_visible(),
    )

    assert payload["root_id"] == "sensor.root"
    assert payload["expansion"]["added_node_ids"] == [
        "sensor.shared_parent"
    ]
    shared = next(
        node for node in payload["nodes"]
        if node["id"] == "sensor.shared_parent"
    )
    assert shared["roles"] == []


def test_expansion_is_deterministic_bounded_and_reports_truncation() -> None:
    graph = _graph()
    graph.add_node(Node("script.another", "script", "Another"))
    graph.add_edge(
        Edge(
            "automation.child",
            "script.another",
            RelationType.CALLS_SCRIPT,
            source_parser="test",
        )
    )

    payload = expand_panel_graph(
        graph,
        "sensor.root",
        "automation.child",
        direction="children",
        visible_node_ids=_visible(),
        max_nodes=4,
    )

    assert payload["truncated"] is True
    assert payload["expansion"]["added_node_ids"] == ["script.another"]
    assert payload["expansion"]["omitted_node_count"] == 1
    assert payload["statistics"]["omitted_node_count"] == 1
    assert any("Expansion truncated" in warning for warning in payload["warnings"])


def test_expansion_filters_structural_neighbours_by_default() -> None:
    payload = expand_panel_graph(
        _graph(),
        "sensor.root",
        "sensor.root",
        direction="children",
        visible_node_ids=_visible(),
    )

    assert "device-1" not in [node["id"] for node in payload["nodes"]]
    assert payload["expansion"]["already_loaded"] is True


def test_expansion_requires_root_and_target_to_be_visible() -> None:
    graph = _graph()

    with pytest.raises(ValueError, match="root_id"):
        expand_panel_graph(
            graph,
            "sensor.root",
            "automation.child",
            direction="children",
            visible_node_ids=["automation.child"],
        )

    with pytest.raises(ValueError, match="node_id"):
        expand_panel_graph(
            graph,
            "sensor.root",
            "automation.child",
            direction="children",
            visible_node_ids=["sensor.root"],
        )


def test_expansion_rejects_invalid_direction_and_existing_over_limit() -> None:
    graph = _graph()

    with pytest.raises(ValueError, match="direction"):
        expand_panel_graph(
            graph,
            "sensor.root",
            "sensor.root",
            direction="sideways",  # type: ignore[arg-type]
            visible_node_ids=_visible(),
        )

    with pytest.raises(ValueError, match="exceeds"):
        expand_panel_graph(
            graph,
            "sensor.root",
            "sensor.root",
            direction="children",
            visible_node_ids=_visible(),
            max_nodes=2,
        )
