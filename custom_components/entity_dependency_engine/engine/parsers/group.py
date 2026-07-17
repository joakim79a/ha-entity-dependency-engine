from __future__ import annotations
from pathlib import Path
from ..model import Confidence, Edge, Node, RelationType
from .base import ParserResult
from .json_storage import read_storage_json

PARSER_NAME = "group"
EXPECTED_STORAGE_KEY = "core.config_entries"
DOMAIN = "group"

def parse_group_relations(config_entries_path: str | Path, entity_nodes: list[Node]) -> ParserResult:
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
            result.warnings.append(f"{path}: invalid group entry")
            continue
        members = options.get("entities")
        if not isinstance(members, list) or not members:
            result.warnings.append(f"{path}: group has no valid entities list")
            continue
        group_nodes = targets.get(entry_id, [])
        if not group_nodes:
            result.warnings.append(f"{path}: no entity found for group {entry_id}")
            continue
        for member in members:
            if not isinstance(member, str):
                result.warnings.append(f"{path}: invalid group member")
                continue
            if member not in known:
                result.warnings.append(f"{path}: group references unknown entity {member}")
            for target in group_nodes:
                result.edges.append(Edge(
                    source_node_id=member,
                    target_node_id=target.node_id,
                    relation_type=RelationType.MEMBER_OF,
                    source_parser=PARSER_NAME,
                    confidence=Confidence.CERTAIN,
                    source_file=EXPECTED_STORAGE_KEY,
                    source_path=f"{path}.options.entities",
                    explanation="group member contributes to group entity",
                    metadata={
                        "group_type": options.get("group_type"),
                        "all": options.get("all"),
                        "hide_members": options.get("hide_members"),
                    },
                ))
    return result
