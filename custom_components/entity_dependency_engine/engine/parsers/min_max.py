"""Parser for GUI-created min_max entities."""

from __future__ import annotations

from pathlib import Path

from ..model import Confidence, Edge, Node, RelationType
from .base import ParserResult
from .json_storage import read_storage_json


PARSER_NAME = "min_max"
EXPECTED_STORAGE_KEY = "core.config_entries"
DOMAIN = "min_max"


class MinMaxFormatError(RuntimeError):
    """Raised when core.config_entries has an unsupported structure."""


def parse_min_max_relations(
    config_entries_path: str | Path,
    entity_nodes: list[Node],
) -> ParserResult:
    """Create source entities -> min_max entity relations."""
    payload = read_storage_json(config_entries_path)

    if payload.get("key") != EXPECTED_STORAGE_KEY:
        raise MinMaxFormatError(
            f"Expected {EXPECTED_STORAGE_KEY!r}, got {payload.get('key')!r}"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise MinMaxFormatError("Missing or invalid data object")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise MinMaxFormatError("Missing or invalid data.entries list")

    targets_by_entry = _targets_by_config_entry(entity_nodes)
    known_entity_ids = {
        node.node_id for node in entity_nodes if node.node_type == "entity"
    }

    result = ParserResult()

    for index, entry in enumerate(entries):
        source_path = f"data.entries[{index}]"

        if not isinstance(entry, dict) or entry.get("domain") != DOMAIN:
            continue

        entry_id = entry.get("entry_id")
        if not isinstance(entry_id, str):
            result.warnings.append(f"{source_path}: missing entry_id")
            continue

        options = entry.get("options")
        if not isinstance(options, dict):
            result.warnings.append(f"{source_path}: invalid options")
            continue

        raw_sources = options.get("entity_ids")
        if not isinstance(raw_sources, list) or not raw_sources:
            result.warnings.append(
                f"{source_path}: min_max has no valid entity_ids list"
            )
            continue

        targets = targets_by_entry.get(entry_id, [])
        if not targets:
            result.warnings.append(
                f"{source_path}: no entity found for min_max {entry_id}"
            )
            continue

        for source_entity in raw_sources:
            if not isinstance(source_entity, str) or not source_entity.strip():
                result.warnings.append(
                    f"{source_path}: invalid min_max source reference"
                )
                continue

            if source_entity not in known_entity_ids:
                result.warnings.append(
                    f"{source_path}: min_max references unknown entity "
                    f"{source_entity}"
                )

            for target in targets:
                result.edges.append(
                    Edge(
                        source_node_id=source_entity,
                        target_node_id=target.node_id,
                        relation_type=RelationType.SOURCE_OF,
                        source_parser=PARSER_NAME,
                        confidence=Confidence.CERTAIN,
                        source_file=EXPECTED_STORAGE_KEY,
                        source_path=f"{source_path}.options.entity_ids",
                        explanation=(
                            "min_max options.entity_ids contributes to "
                            "the calculated entity"
                        ),
                        metadata={
                            "calculation_type": options.get("type"),
                            "round_digits": options.get("round_digits"),
                        },
                    )
                )

    return result


def _targets_by_config_entry(
    entity_nodes: list[Node],
) -> dict[str, list[Node]]:
    index: dict[str, list[Node]] = {}

    for node in entity_nodes:
        if node.node_type != "entity":
            continue
        if node.metadata.get("platform") != DOMAIN:
            continue

        entry_id = node.metadata.get("config_entry_id")
        if isinstance(entry_id, str):
            index.setdefault(entry_id, []).append(node)

    return index
