from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node
from engine.parsers.derivative import (
    parse_derivative_relations,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "core.config_entries.derivative.sample"
)


def _nodes() -> list[Node]:
    return [
        Node(
            "sensor.return_temperature",
            "entity",
            metadata={"platform": "shelly"},
        ),
        Node(
            "sensor.derivative_retur_lvp",
            "entity",
            metadata={
                "platform": "derivative",
                "config_entry_id": "derivative_1",
            },
        ),
    ]


def test_parse_derivative_relation() -> None:
    result = parse_derivative_relations(FIXTURE, _nodes())

    assert len(result.edges) == 1
    assert result.warnings == []

    edge = result.edges[0]
    assert edge.source_node_id == "sensor.return_temperature"
    assert edge.target_node_id == "sensor.derivative_retur_lvp"
    assert edge.metadata["unit_time"] == "h"
    assert edge.metadata["time_window"]["minutes"] == 15


def test_relation_populates_graph() -> None:
    nodes = _nodes()
    result = parse_derivative_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert graph.children("sensor.return_temperature") == frozenset(
        {"sensor.derivative_retur_lvp"}
    )
    assert graph.parents("sensor.derivative_retur_lvp") == frozenset(
        {"sensor.return_temperature"}
    )


def test_unknown_source_is_preserved_as_warning(tmp_path: Path) -> None:
    fixture = tmp_path / "entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{"entries":[{
            "domain":"derivative",
            "entry_id":"derivative_1",
            "options":{"source":"sensor.deleted_temperature"}
          }]}
        }
        """,
        encoding="utf-8",
    )

    result = parse_derivative_relations(fixture, _nodes())

    assert len(result.edges) == 1
    assert len(result.warnings) == 1
