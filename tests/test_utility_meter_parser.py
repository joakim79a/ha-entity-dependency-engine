from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node
from engine.parsers.utility_meter import (
    parse_utility_meter_relations,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "core.config_entries.utility_meter.sample"
)


def _nodes() -> list[Node]:
    return [
        Node(
            "sensor.vvb_energy",
            "entity",
            metadata={"platform": "shelly"},
        ),
        Node(
            "sensor.vvb_kwh_dag",
            "entity",
            metadata={
                "platform": "utility_meter",
                "config_entry_id": "um_1",
            },
        ),
    ]


def test_parse_utility_meter_relation() -> None:
    result = parse_utility_meter_relations(FIXTURE, _nodes())

    assert len(result.edges) == 1
    assert result.warnings == []

    edge = result.edges[0]
    assert edge.source_node_id == "sensor.vvb_energy"
    assert edge.target_node_id == "sensor.vvb_kwh_dag"
    assert edge.metadata["cycle"] == "daily"


def test_relation_populates_graph() -> None:
    nodes = _nodes()
    result = parse_utility_meter_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert graph.children("sensor.vvb_energy") == frozenset(
        {"sensor.vvb_kwh_dag"}
    )
    assert graph.parents("sensor.vvb_kwh_dag") == frozenset(
        {"sensor.vvb_energy"}
    )


def test_unknown_source_is_preserved_as_warning(tmp_path: Path) -> None:
    fixture = tmp_path / "entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{"entries":[{
            "domain":"utility_meter",
            "entry_id":"um_1",
            "options":{"source":"sensor.deleted_energy"}
          }]}
        }
        """,
        encoding="utf-8",
    )

    result = parse_utility_meter_relations(fixture, _nodes())

    assert len(result.edges) == 1
    assert len(result.warnings) == 1
