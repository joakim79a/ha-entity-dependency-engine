from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node
from engine.parsers.integration_sensor import (
    parse_integration_relations,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "core.config_entries.integration.sample"
)


def _nodes() -> list[Node]:
    return [
        Node(
            "sensor.vvb_power",
            "entity",
            metadata={"platform": "shelly"},
        ),
        Node(
            "sensor.vvb_energy_integrated",
            "entity",
            metadata={
                "platform": "integration",
                "config_entry_id": "integration_1",
            },
        ),
    ]


def test_parse_integration_relation() -> None:
    result = parse_integration_relations(FIXTURE, _nodes())

    assert len(result.edges) == 1
    assert result.warnings == []

    edge = result.edges[0]
    assert edge.source_node_id == "sensor.vvb_power"
    assert edge.target_node_id == "sensor.vvb_energy_integrated"
    assert edge.metadata["method"] == "left"
    assert edge.metadata["unit_time"] == "h"


def test_relation_populates_graph() -> None:
    nodes = _nodes()
    result = parse_integration_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert graph.children("sensor.vvb_power") == frozenset(
        {"sensor.vvb_energy_integrated"}
    )


def test_unknown_source_is_preserved_as_warning(tmp_path: Path) -> None:
    fixture = tmp_path / "entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{"entries":[{
            "domain":"integration",
            "entry_id":"integration_1",
            "options":{"source":"sensor.deleted_power"}
          }]}
        }
        """,
        encoding="utf-8",
    )

    result = parse_integration_relations(fixture, _nodes())

    assert len(result.edges) == 1
    assert len(result.warnings) == 1
