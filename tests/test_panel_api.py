"""Tests for pure panel API helpers."""

from __future__ import annotations

from pathlib import Path

from engine.builder import BuildPaths, BuildResult, BuildStatistics
from engine.graph import DirectedGraph
from engine.model import Edge, Node, RelationType
from engine.panel_api import (
    PanelGraphCache,
    search_graph_entities,
)


def _build_result(graph: DirectedGraph) -> BuildResult:
    paths = BuildPaths.from_config_dir("/tmp/config")
    return BuildResult(
        graph=graph,
        warnings=[],
        statistics=BuildStatistics(),
        paths=paths,
    )


def _search_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node(
                "sensor.pool_temperature",
                "entity",
                "Pool temperature registry name",
                metadata={"domain": "sensor", "platform": "template"},
            ),
            Node(
                "automation.pool_control",
                "automation",
                "Pool control",
                metadata={"domain": "automation"},
            ),
            Node("device-1", "device", "Pool device"),
        ]
    )
    graph.add_edge(
        Edge(
            "sensor.pool_temperature",
            "automation.pool_control",
            RelationType.TRIGGERS,
            source_parser="test",
        )
    )
    return graph


def test_search_prefers_friendly_name_and_excludes_structural_nodes() -> None:
    result = search_graph_entities(
        _search_graph(),
        runtime_entities={
            "sensor.pool_temperature": {
                "friendly_name": "Swimming pool temperature",
                "state": "27.4",
                "state_display": "27.4 °C",
                "available": True,
                "icon": "mdi:pool-thermometer",
                "device_name": "Pool controller",
                "area_name": "Garden",
                "integration": "template",
            }
        },
        query="swimming",
    )

    assert result["count"] == 1
    assert result["total"] == 1
    assert result["entities"][0] == {
        "entity_id": "sensor.pool_temperature",
        "display_name": "Swimming pool temperature",
        "domain": "sensor",
        "icon": "mdi:pool-thermometer",
        "state": "27.4",
        "state_display": "27.4 °C",
        "available": True,
        "platform": "template",
        "device_name": "Pool controller",
        "area_name": "Garden",
        "parent_count": 0,
        "child_count": 1,
        "broken": False,
    }


def test_search_matches_entity_id_context_and_has_deterministic_limit() -> None:
    graph = _search_graph()

    by_id = search_graph_entities(graph, query="automation.pool")
    by_context = search_graph_entities(
        graph,
        runtime_entities={
            "sensor.pool_temperature": {"area_name": "Back garden"}
        },
        query="back garden",
    )
    limited = search_graph_entities(graph, query="", limit=1)

    assert [item["entity_id"] for item in by_id["entities"]] == [
        "automation.pool_control"
    ]
    assert [item["entity_id"] for item in by_context["entities"]] == [
        "sensor.pool_temperature"
    ]
    assert limited["count"] == 1
    assert limited["total"] == 2


def test_search_rejects_invalid_limit() -> None:
    try:
        search_graph_entities(_search_graph(), limit=0)
    except ValueError as err:
        assert "limit" in str(err)
    else:
        raise AssertionError("Expected ValueError")


def test_panel_graph_cache_reuses_and_refreshes_build(monkeypatch, tmp_path: Path) -> None:
    graph = DirectedGraph()
    graph.add_node(Node("sensor.root", "entity", "Root"))
    build = _build_result(graph)
    calls: list[Path] = []

    def fake_build_graph(config_dir: str | Path) -> BuildResult:
        calls.append(Path(config_dir))
        return build

    monkeypatch.setattr(
        "engine.panel_api.build_graph",
        fake_build_graph,
    )

    cache = PanelGraphCache()

    first = cache.get(tmp_path)
    second = cache.get(tmp_path)
    refreshed = cache.get(tmp_path, refresh=True)

    assert first is build
    assert second is build
    assert refreshed is build
    assert len(calls) == 2

    cache.clear()
    cache.get(tmp_path)
    assert len(calls) == 3
