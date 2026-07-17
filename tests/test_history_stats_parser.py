from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node
from engine.parsers.history_stats import (
    parse_history_stats_relations,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "core.config_entries.history_stats.sample"
)


def _nodes() -> list[Node]:
    return [
        Node(
            "binary_sensor.elpris_under_offpeak1",
            "entity",
            metadata={"platform": "template"},
        ),
        Node(
            "sensor.tid_elpris_under_offpeak1",
            "entity",
            metadata={
                "platform": "history_stats",
                "config_entry_id": "history_1",
            },
        ),
    ]


def test_parse_history_stats_relation() -> None:
    result = parse_history_stats_relations(FIXTURE, _nodes())

    assert len(result.edges) == 1
    assert result.warnings == []

    edge = result.edges[0]
    assert edge.source_node_id == "binary_sensor.elpris_under_offpeak1"
    assert edge.target_node_id == "sensor.tid_elpris_under_offpeak1"
    assert edge.metadata["type"] == "time"
    assert edge.metadata["state"] == ["on"]


def test_relation_populates_graph() -> None:
    nodes = _nodes()
    result = parse_history_stats_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert graph.children(
        "binary_sensor.elpris_under_offpeak1"
    ) == frozenset({"sensor.tid_elpris_under_offpeak1"})


def test_unknown_source_is_preserved_as_warning(tmp_path: Path) -> None:
    fixture = tmp_path / "entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{"entries":[{
            "domain":"history_stats",
            "entry_id":"history_1",
            "options":{"entity_id":"binary_sensor.deleted_source"}
          }]}
        }
        """,
        encoding="utf-8",
    )

    result = parse_history_stats_relations(fixture, _nodes())

    assert len(result.edges) == 1
    assert len(result.warnings) == 1
