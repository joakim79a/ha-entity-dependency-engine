"""Parser for GUI-created utility_meter entities."""

from __future__ import annotations

from pathlib import Path

from ..model import Confidence, Edge, Node, RelationType
from .base import ParserResult
from .json_storage import read_storage_json


PARSER_NAME = "utility_meter"
EXPECTED_STORAGE_KEY = "core.config_entries"
DOMAIN = "utility_meter"


class UtilityMeterFormatError(RuntimeError):
    """Raised when core.config_entries has an unsupported structure."""


def parse_utility_meter_relations(
    config_entries_path: str | Path,
    entity_nodes: list[Node],
) -> ParserResult:
    """Create source entity -> utility meter entity relations."""
    payload = read_storage_json(config_entries_path)

    if payload.get("key") != EXPECTED_STORAGE_KEY:
        raise UtilityMeterFormatError(
            f"Expected {EXPECTED_STORAGE_KEY!r}, got {payload.get('key')!r}"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise UtilityMeterFormatError("Missing or invalid data object")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise UtilityMeterFormatError("Missing or invalid data.entries list")

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

        source_entity = options.get("source")
        if not isinstance(source_entity, str) or not source_entity.strip():
            result.warnings.append(
                f"{source_path}: utility meter has no valid source entity"
            )
            continue

        targets = targets_by_entry.get(entry_id, [])
        if not targets:
            result.warnings.append(
                f"{source_path}: no entity found for utility meter {entry_id}"
            )
            continue

        if source_entity not in known_entity_ids:
            result.warnings.append(
                f"{source_path}: utility meter references unknown entity "
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
                    source_path=f"{source_path}.options.source",
                    explanation=(
                        "utility_meter options.source feeds the meter entity"
                    ),
                    metadata={
                        "cycle": options.get("cycle"),
                        "offset": options.get("offset"),
                        "tariffs": options.get("tariffs", []),
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
