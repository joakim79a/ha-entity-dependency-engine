from pathlib import Path

from engine.graph import DirectedGraph
from engine.model import Node
from engine.parsers.gui_templates import (
    parse_gui_template_relations,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "core.config_entries.templates.sample"
)


def _entity_nodes() -> list[Node]:
    return [
        Node(
            "sensor.pulse_elpris",
            "entity",
            metadata={"platform": "tibber"},
        ),
        Node(
            "input_number.elskatt_kop",
            "entity",
            metadata={"platform": "input_number"},
        ),
        Node(
            "binary_sensor.elpris_under_medel",
            "entity",
            metadata={
                "platform": "template",
                "config_entry_id": "template_entry_1",
            },
        ),
        Node(
            "sensor.kost_el_kop",
            "entity",
            metadata={
                "platform": "template",
                "config_entry_id": "template_entry_2",
            },
        ),
    ]


def test_parse_gui_template_relations() -> None:
    result = parse_gui_template_relations(FIXTURE, _entity_nodes())

    pairs = {
        (edge.source_node_id, edge.target_node_id)
        for edge in result.edges
    }

    assert pairs == {
        (
            "sensor.pulse_elpris",
            "binary_sensor.elpris_under_medel",
        ),
        ("sensor.pulse_elpris", "sensor.kost_el_kop"),
        ("input_number.elskatt_kop", "sensor.kost_el_kop"),
    }


def test_duplicate_references_across_template_are_collapsed_per_path() -> None:
    result = parse_gui_template_relations(FIXTURE, _entity_nodes())

    pulse_to_first = [
        edge
        for edge in result.edges
        if edge.source_node_id == "sensor.pulse_elpris"
        and edge.target_node_id == "binary_sensor.elpris_under_medel"
    ]

    assert len(pulse_to_first) == 1


def test_relations_populate_graph() -> None:
    nodes = _entity_nodes()
    result = parse_gui_template_relations(FIXTURE, nodes)

    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)

    assert graph.children("sensor.pulse_elpris") == frozenset(
        {
            "binary_sensor.elpris_under_medel",
            "sensor.kost_el_kop",
        }
    )

    assert graph.parents("sensor.kost_el_kop") == frozenset(
        {
            "sensor.pulse_elpris",
            "input_number.elskatt_kop",
        }
    )


def test_probable_unknown_non_entity_domain_is_ignored(tmp_path: Path) -> None:
    fixture = tmp_path / "config_entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{
            "entries":[
              {
                "domain":"template",
                "entry_id":"template_entry_2",
                "options":{
                  "state":"{{ states.sensor | list }} {{ ns.total_value }}"
                }
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )

    result = parse_gui_template_relations(fixture, _entity_nodes())

    assert result.edges == []
    assert result.warnings == []


def test_probable_unknown_real_domain_is_preserved(tmp_path: Path) -> None:
    fixture = tmp_path / "config_entries.json"
    fixture.write_text(
        """
        {
          "key":"core.config_entries",
          "data":{
            "entries":[
              {
                "domain":"template",
                "entry_id":"template_entry_2",
                "options":{
                  "state":"{{ some_macro('sensor.deleted_source') }}"
                }
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )

    result = parse_gui_template_relations(fixture, _entity_nodes())

    assert len(result.edges) == 1
    assert result.edges[0].source_node_id == "sensor.deleted_source"
    assert len(result.warnings) == 1
