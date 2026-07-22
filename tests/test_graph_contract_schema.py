"""Validate graph contract examples and serializer output."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from engine.graph import DirectedGraph
from engine.model import Confidence, Edge, Node, RelationType
from engine.panel_graph import serialize_panel_graph


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "graph-data.schema.json"
EXAMPLE_DIR = ROOT / "docs" / "examples"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_semantics(payload: dict) -> None:
    node_ids = [node["id"] for node in payload["nodes"]]
    edge_ids = [edge["id"] for edge in payload["edges"]]
    node_id_set = set(node_ids)

    assert len(node_ids) == len(node_id_set)
    assert len(edge_ids) == len(set(edge_ids))
    assert payload["root_id"] in node_id_set

    assert payload["statistics"]["node_count"] == len(node_ids)
    assert payload["statistics"]["edge_count"] == len(payload["edges"])
    assert payload["statistics"]["omitted_node_count"] == (
        payload["statistics"]["total_node_count"] - len(node_ids)
    )
    assert payload["truncated"] is (
        payload["statistics"]["omitted_node_count"] > 0
    )

    for edge in payload["edges"]:
        assert edge["source"] in node_id_set
        assert edge["target"] in node_id_set


def _example_paths() -> list[Path]:
    return sorted(EXAMPLE_DIR.glob("graph-*.json"))


def test_graph_contract_schema_is_valid() -> None:
    _validator()


@pytest.mark.parametrize("example_path", _example_paths())
def test_documented_graph_examples_validate(example_path: Path) -> None:
    payload = _load_json(example_path)

    _validator().validate(payload)
    _validate_semantics(payload)


def test_serializer_output_validates_against_contract() -> None:
    graph = DirectedGraph()
    graph.add_nodes(
        [
            Node(
                "sensor.source",
                "entity",
                "Source",
                metadata={"domain": "sensor", "platform": "mqtt"},
            ),
            Node(
                "sensor.root",
                "entity",
                "Root",
                metadata={"domain": "sensor", "platform": "template"},
            ),
            Node(
                "automation.consumer",
                "automation",
                "Consumer",
                metadata={"domain": "automation"},
            ),
        ]
    )
    graph.add_edges(
        [
            Edge(
                "sensor.source",
                "sensor.root",
                RelationType.READS,
                source_parser="test",
                confidence=Confidence.CERTAIN,
            ),
            Edge(
                "sensor.root",
                "automation.consumer",
                RelationType.TRIGGERS,
                source_parser="test",
                confidence=Confidence.CERTAIN,
            ),
        ]
    )

    payload = serialize_panel_graph(
        graph,
        "sensor.root",
        revision="schema-test-v1",
    )

    _validator().validate(payload)
    _validate_semantics(payload)


def test_schema_rejects_missing_required_field() -> None:
    payload = _load_json(EXAMPLE_DIR / "graph-direct.json")
    invalid = deepcopy(payload)
    invalid.pop("root_id")

    with pytest.raises(ValidationError):
        _validator().validate(invalid)


def test_semantic_check_rejects_dangling_edge() -> None:
    payload = _load_json(EXAMPLE_DIR / "graph-direct.json")
    invalid = deepcopy(payload)
    invalid["edges"][0]["target"] = "sensor.not_returned"

    # JSON Schema validates field shape. Cross-object graph integrity is
    # deliberately enforced by the semantic contract check.
    _validator().validate(invalid)

    with pytest.raises(AssertionError):
        _validate_semantics(invalid)


def test_semantic_check_rejects_duplicate_node_ids() -> None:
    payload = _load_json(EXAMPLE_DIR / "graph-direct.json")
    invalid = deepcopy(payload)
    invalid["nodes"].append(deepcopy(invalid["nodes"][0]))
    invalid["statistics"]["node_count"] += 1
    invalid["statistics"]["total_node_count"] += 1

    _validator().validate(invalid)

    with pytest.raises(AssertionError):
        _validate_semantics(invalid)
