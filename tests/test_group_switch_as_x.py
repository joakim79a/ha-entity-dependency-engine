from pathlib import Path
from engine.graph import DirectedGraph
from engine.model import Node, RelationType
from engine.parsers.group import parse_group_relations
from engine.parsers.switch_as_x import parse_switch_as_x_relations

FIXTURE = Path(__file__).parent / "fixtures" / "core.config_entries.group_switch_as_x.sample"

def test_group_relations():
    nodes = [
        Node("light.kitchen_one", "entity", metadata={"platform":"test"}),
        Node("light.kitchen_two", "entity", metadata={"platform":"test"}),
        Node("light.kitchen_group", "entity", metadata={"platform":"group","config_entry_id":"group_1"}),
    ]
    result = parse_group_relations(FIXTURE, nodes)
    assert len(result.edges) == 2
    assert result.warnings == []
    graph = DirectedGraph()
    graph.add_nodes(nodes)
    graph.add_edges(result.edges)
    assert graph.parents("light.kitchen_group") == frozenset({"light.kitchen_one","light.kitchen_two"})
    assert all(e.relation_type == RelationType.MEMBER_OF for e in result.edges)

def test_switch_as_x_relation():
    nodes = [
        Node("switch.raw_spot", "entity", metadata={"platform":"shelly"}),
        Node("light.converted_spot", "entity", metadata={"platform":"switch_as_x","config_entry_id":"switch_as_x_1"}),
    ]
    result = parse_switch_as_x_relations(FIXTURE, nodes)
    assert len(result.edges) == 1
    assert result.warnings == []
    edge = result.edges[0]
    assert edge.source_node_id == "switch.raw_spot"
    assert edge.target_node_id == "light.converted_spot"
    assert edge.relation_type == RelationType.SOURCE_OF
