from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node
from engine.parsers.threshold import (
    parse_threshold_relations,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "core.config_entries.threshold.sample"
)


def _nodes() -> list[Node]:
    return [
        Node(
            "sensor.lvp1_total_w",
            "entity",
            metadata={"platform": "template"},
        ),
        Node(
            "binary_sensor.lvp1_kompressor",
            "entity",
            metadata={
                "platform": "threshold",
                "config_entry_id": "threshold_1",
            },
        ),
    ]


def test_parse_threshold_relation() -> None:
    result = parse_threshold_relations(FIXTURE, _nodes())

    assert len(result.edges) == 1
    assert result.warnings == []

    edge = result.edges[0]
    assert edge.source_node_id == "sensor.lvp1_total_w"
    assert edge.target_node_id == "binary_sensor.lvp1_kompressor"
    assert edge.metadata["upper"] == 500.0
    assert edge.metadata["lower"] is None
    assert edge.metadata["hysteresis"] == 0.0


def test_relation_populates_graph() -> None:
    nodes = _nodes()
    result = parse_threshold_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert graph.children("sensor.lvp1_total_w") == frozenset(
        {"binary_sensor.lvp1_kompressor"}
    )
    assert graph.parents("binary_sensor.lvp1_kompressor") == frozenset(
        {"sensor.lvp1_total_w"}
    )


def test_unknown_source_is_preserved_as_warning(tmp_path: Path) -> None:
    fixture = tmp_path / "entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{"entries":[{
            "domain":"threshold",
            "entry_id":"threshold_1",
            "options":{"entity_id":"sensor.deleted_power"}
          }]}
        }
        """,
        encoding="utf-8",
    )

    result = parse_threshold_relations(fixture, _nodes())

    assert len(result.edges) == 1
    assert len(result.warnings) == 1
