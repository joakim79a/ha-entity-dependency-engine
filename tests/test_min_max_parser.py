from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node
from engine.parsers.min_max import parse_min_max_relations


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "core.config_entries.min_max.sample"
)


def _nodes() -> list[Node]:
    return [
        Node("sensor.phase_a_power", "entity", metadata={"platform": "shelly"}),
        Node("sensor.phase_b_power", "entity", metadata={"platform": "shelly"}),
        Node("sensor.phase_c_power", "entity", metadata={"platform": "shelly"}),
        Node(
            "sensor.3em_w_totalt",
            "entity",
            metadata={
                "platform": "min_max",
                "config_entry_id": "minmax_1",
            },
        ),
    ]


def test_parse_all_min_max_sources() -> None:
    result = parse_min_max_relations(FIXTURE, _nodes())

    assert len(result.edges) == 3
    assert result.warnings == []

    pairs = {
        (edge.source_node_id, edge.target_node_id)
        for edge in result.edges
    }

    assert pairs == {
        ("sensor.phase_a_power", "sensor.3em_w_totalt"),
        ("sensor.phase_b_power", "sensor.3em_w_totalt"),
        ("sensor.phase_c_power", "sensor.3em_w_totalt"),
    }

    assert all(
        edge.metadata["calculation_type"] == "sum"
        for edge in result.edges
    )


def test_relations_populate_graph() -> None:
    nodes = _nodes()
    result = parse_min_max_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert graph.parents("sensor.3em_w_totalt") == frozenset(
        {
            "sensor.phase_a_power",
            "sensor.phase_b_power",
            "sensor.phase_c_power",
        }
    )


def test_unknown_source_is_preserved_as_warning(tmp_path: Path) -> None:
    fixture = tmp_path / "entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{"entries":[{
            "domain":"min_max",
            "entry_id":"minmax_1",
            "options":{
              "entity_ids":["sensor.phase_a_power","sensor.deleted_phase"],
              "type":"sum"
            }
          }]}
        }
        """,
        encoding="utf-8",
    )

    result = parse_min_max_relations(fixture, _nodes())

    assert len(result.edges) == 2
    assert len(result.warnings) == 1
