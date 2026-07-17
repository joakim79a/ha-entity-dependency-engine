from __future__ import annotations
from pathlib import Path
from ..model import Confidence, Edge, Node, RelationType
from .base import ParserResult
from .json_storage import read_storage_json

PARSER_NAME = "switch_as_x"
EXPECTED_STORAGE_KEY = "core.config_entries"
DOMAIN = "switch_as_x"

def parse_switch_as_x_relations(config_entries_path: str | Path, entity_nodes: list[Node]) -> ParserResult:
    payload = read_storage_json(config_entries_path)
    if payload.get("key") != EXPECTED_STORAGE_KEY:
        raise RuntimeError(f"Expected {EXPECTED_STORAGE_KEY!r}")
    entries = payload.get("data", {}).get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("Missing or invalid data.entries list")

    targets: dict[str, list[Node]] = {}
    known = {n.node_id for n in entity_nodes if n.node_type == "entity"}
    for node in entity_nodes:
        if node.node_type == "entity" and node.metadata.get("platform") == DOMAIN:
            entry_id = node.metadata.get("config_entry_id")
            if isinstance(entry_id, str):
                targets.setdefault(entry_id, []).append(node)

    result = ParserResult()
    for index, entry in enumerate(entries):
        path = f"data.entries[{index}]"
        if not isinstance(entry, dict) or entry.get("domain") != DOMAIN:
            continue
        entry_id = entry.get("entry_id")
        options = entry.get("options")
        if not isinstance(entry_id, str) or not isinstance(options, dict):
            result.warnings.append(f"{path}: invalid switch_as_x entry")
            continue
        source = options.get("entity_id")
        if not isinstance(source, str):
            result.warnings.append(f"{path}: switch_as_x has no valid entity_id")
            continue
        target_nodes = targets.get(entry_id, [])
        if not target_nodes:
            result.warnings.append(f"{path}: no entity found for switch_as_x {entry_id}")
            continue
        if source not in known:
            result.warnings.append(f"{path}: switch_as_x references unknown entity {source}")
        for target in target_nodes:
            result.edges.append(Edge(
                source_node_id=source,
                target_node_id=target.node_id,
                relation_type=RelationType.SOURCE_OF,
                source_parser=PARSER_NAME,
                confidence=Confidence.CERTAIN,
                source_file=EXPECTED_STORAGE_KEY,
                source_path=f"{path}.options.entity_id",
                explanation="source switch backs converted entity",
                metadata={
                    "target_domain": options.get("target_domain"),
                    "invert": options.get("invert"),
                },
            ))
    return result
