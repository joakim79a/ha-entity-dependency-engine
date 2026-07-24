"""Tests for the panel graph contract serializer."""

from __future__ import annotations

import json

import pytest

from engine.graph import DirectedGraph
from engine.model import Confidence, Edge, Node, RelationType
from engine.panel_graph import serialize_panel_graph


def _add_edge(
    graph: DirectedGraph,
    source: str,
    target: str,
    relation: RelationType = RelationType.REFERENCES,
    *,
    parser: str = "test",
) -> None:
    graph.add_edge(
        Edge(
            source,
            target,
            relation,
            source_parser=parser,
            confidence=Confidence.CERTAIN,
        )
    )


def _line_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node("sensor.grandparent", "entity", "Grandparent"),
            Node("sensor.parent", "entity", "Parent"),
            Node("sensor.root", "entity", "Root"),
            Node("sensor.child", "entity", "Child"),
            Node("sensor.grandchild", "entity", "Grandchild"),
        ]
    )
    _add_edge(graph, "sensor.grandparent", "sensor.parent")
    _add_edge(graph, "sensor.parent", "sensor.root")
    _add_edge(graph, "sensor.root", "sensor.child")
    _add_edge(graph, "sensor.child", "sensor.grandchild")
    return graph


def _node_ids(payload: dict) -> list[str]:
    return [node["id"] for node in payload["nodes"]]


def _node(payload: dict, node_id: str) -> dict:
    return next(node for node in payload["nodes"] if node["id"] == node_id)


def test_direct_scope_returns_one_level_in_both_directions() -> None:
    payload = serialize_panel_graph(_line_graph(), "sensor.root")

    assert payload["schema_version"] == 1
    assert payload["scope"] == "direct"
    assert _node_ids(payload) == [
        "sensor.root",
        "sensor.parent",
        "sensor.child",
    ]
    assert payload["statistics"] == {
        "node_count": 3,
        "edge_count": 2,
        "total_node_count": 3,
        "omitted_node_count": 0,
        "broken_reference_count": 0,
        "cycle_component_count": 0,
    }
    assert _node(payload, "sensor.parent")["roles"] == ["parent"]
    assert _node(payload, "sensor.child")["roles"] == ["child"]
    assert _node(payload, "sensor.parent")["parents_loaded"] is False
    assert _node(payload, "sensor.child")["children_loaded"] is False


def test_all_scopes_follow_parent_to_child_direction() -> None:
    graph = _line_graph()

    parents = serialize_panel_graph(
        graph, "sensor.root", scope="all_parents"
    )
    children = serialize_panel_graph(
        graph, "sensor.root", scope="all_children"
    )
    complete = serialize_panel_graph(graph, "sensor.root", scope="all")

    assert _node_ids(parents) == [
        "sensor.root",
        "sensor.parent",
        "sensor.grandparent",
    ]
    assert _node_ids(children) == [
        "sensor.root",
        "sensor.child",
        "sensor.grandchild",
    ]
    assert _node_ids(complete) == [
        "sensor.root",
        "sensor.parent",
        "sensor.child",
        "sensor.grandparent",
        "sensor.grandchild",
    ]
    assert _node(complete, "sensor.grandparent")["upstream_depth"] == 2
    assert _node(complete, "sensor.grandchild")["downstream_depth"] == 2


def test_friendly_name_enrichment_is_primary_and_context_is_allow_listed() -> None:
    graph = DirectedGraph()
    graph.add_node(
        Node(
            "sensor.root",
            "entity",
            "Registry name",
            metadata={
                "domain": "sensor",
                "platform": "template",
                "device_id": "device-1",
                "secret": "must-not-leak",
            },
        )
    )

    payload = serialize_panel_graph(
        graph,
        "sensor.root",
        runtime_entities={
            "sensor.root": {
                "friendly_name": "Friendly name",
                "state": "27.4",
                "state_display": "27.4 °C",
                "available": True,
                "icon": "mdi:thermometer",
                "device_name": "Pool device",
                "area_name": "Garden",
                "integration": "template",
                "secret": "still-must-not-leak",
            }
        },
    )

    node = payload["nodes"][0]
    assert node["display_name"] == "Friendly name"
    assert node["runtime"] == {
        "state": "27.4",
        "state_display": "27.4 °C",
        "available": True,
        "icon": "mdi:thermometer",
    }
    assert node["context"] == {
        "platform": "template",
        "device_id": "device-1",
        "device_name": "Pool device",
        "area_id": None,
        "area_name": "Garden",
        "config_entry_id": None,
        "integration": "template",
    }
    assert "secret" not in json.dumps(payload)


def test_duplicate_paths_return_one_node_and_both_edges() -> None:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node("sensor.root", "entity", "Root"),
            Node("sensor.left", "entity", "Left"),
            Node("sensor.right", "entity", "Right"),
            Node("sensor.shared", "entity", "Shared"),
        ]
    )
    _add_edge(graph, "sensor.root", "sensor.left")
    _add_edge(graph, "sensor.root", "sensor.right")
    _add_edge(graph, "sensor.left", "sensor.shared")
    _add_edge(graph, "sensor.right", "sensor.shared")

    payload = serialize_panel_graph(
        graph, "sensor.root", scope="all_children"
    )

    assert _node_ids(payload).count("sensor.shared") == 1
    shared_edges = [
        edge for edge in payload["edges"] if edge["target"] == "sensor.shared"
    ]
    assert {(edge["source"], edge["target"]) for edge in shared_edges} == {
        ("sensor.left", "sensor.shared"),
        ("sensor.right", "sensor.shared"),
    }


def test_cycles_terminate_and_are_marked() -> None:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node("sensor.a", "entity", "A"),
            Node("sensor.b", "entity", "B"),
            Node("sensor.c", "entity", "C"),
        ]
    )
    _add_edge(graph, "sensor.a", "sensor.b")
    _add_edge(graph, "sensor.b", "sensor.c")
    _add_edge(graph, "sensor.c", "sensor.a")

    payload = serialize_panel_graph(graph, "sensor.a", scope="all")

    assert set(_node_ids(payload)) == {"sensor.a", "sensor.b", "sensor.c"}
    assert payload["statistics"]["cycle_component_count"] == 1
    assert all(node["in_cycle"] for node in payload["nodes"])
    assert all(edge["cycle_edge"] for edge in payload["edges"])


def test_broken_references_remain_explicit() -> None:
    graph = DirectedGraph()
    graph.add_node(Node("sensor.root", "entity", "Root"))
    graph.add_edge(
        Edge(
            "sensor.root",
            "sensor.missing",
            RelationType.REFERENCES,
            source_parser="test",
        ),
        create_missing_nodes=True,
        missing_node_type="unknown_entity",
    )

    payload = serialize_panel_graph(graph, "sensor.root")

    missing = _node(payload, "sensor.missing")
    assert missing["broken"] is True
    assert payload["statistics"]["broken_reference_count"] == 1


def test_full_scope_truncation_is_deterministic_and_balanced() -> None:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node("sensor.parent_a", "entity", "Parent A"),
            Node("sensor.parent_b", "entity", "Parent B"),
            Node("sensor.root", "entity", "Root"),
            Node("sensor.child_a", "entity", "Child A"),
            Node("sensor.child_b", "entity", "Child B"),
        ]
    )
    _add_edge(graph, "sensor.parent_a", "sensor.root")
    _add_edge(graph, "sensor.parent_b", "sensor.root")
    _add_edge(graph, "sensor.root", "sensor.child_a")
    _add_edge(graph, "sensor.root", "sensor.child_b")

    first = serialize_panel_graph(
        graph, "sensor.root", scope="all", max_nodes=3
    )
    second = serialize_panel_graph(
        graph, "sensor.root", scope="all", max_nodes=3
    )

    assert first == second
    assert _node_ids(first) == [
        "sensor.root",
        "sensor.parent_a",
        "sensor.child_a",
    ]
    assert first["truncated"] is True
    assert first["statistics"]["total_node_count"] == 5
    assert first["statistics"]["omitted_node_count"] == 2


def test_structural_nodes_are_excluded_by_default() -> None:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node("sensor.root", "entity", "Root"),
            Node("device-1", "device", "Device"),
        ]
    )
    _add_edge(
        graph,
        "sensor.root",
        "device-1",
        RelationType.BELONGS_TO_DEVICE,
    )

    default_payload = serialize_panel_graph(graph, "sensor.root")
    structural_payload = serialize_panel_graph(
        graph, "sensor.root", include_structural=True
    )

    assert _node_ids(default_payload) == ["sensor.root"]
    assert _node_ids(structural_payload) == ["sensor.root", "device-1"]
    assert _node(structural_payload, "device-1")["structural"] is True
    assert structural_payload["edges"][0]["structural"] is True


def test_invalid_scope_and_limits_fail_cleanly() -> None:
    graph = DirectedGraph()
    graph.add_node(Node("sensor.root", "entity", "Root"))

    with pytest.raises(ValueError, match="Unsupported graph scope"):
        serialize_panel_graph(graph, "sensor.root", scope="sideways")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="max_nodes"):
        serialize_panel_graph(graph, "sensor.root", max_nodes=0)
