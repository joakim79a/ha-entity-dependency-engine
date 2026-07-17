"""Parser for GUI-created threshold entities."""

from __future__ import annotations

from pathlib import Path

from ..model import Confidence, Edge, Node, RelationType
from .base import ParserResult
from .json_storage import read_storage_json


PARSER_NAME = "threshold"
EXPECTED_STORAGE_KEY = "core.config_entries"
DOMAIN = "threshold"


class ThresholdFormatError(RuntimeError):
    """Raised when core.config_entries has an unsupported structure."""


def parse_threshold_relations(
    config_entries_path: str | Path,
    entity_nodes: list[Node],
) -> ParserResult:
    """Create source entity -> threshold binary sensor relations."""
    payload = read_storage_json(config_entries_path)

    if payload.get("key") != EXPECTED_STORAGE_KEY:
        raise ThresholdFormatError(
            f"Expected {EXPECTED_STORAGE_KEY!r}, got {payload.get('key')!r}"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ThresholdFormatError("Missing or invalid data object")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ThresholdFormatError("Missing or invalid data.entries list")

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

        source_entity = options.get("entity_id")
        if not isinstance(source_entity, str) or not source_entity.strip():
            result.warnings.append(
                f"{source_path}: threshold has no valid entity_id"
            )
            continue

        targets = targets_by_entry.get(entry_id, [])
        if not targets:
            result.warnings.append(
                f"{source_path}: no entity found for threshold {entry_id}"
            )
            continue

        if source_entity not in known_entity_ids:
            result.warnings.append(
                f"{source_path}: threshold references unknown entity "
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
                    source_path=f"{source_path}.options.entity_id",
                    explanation=(
                        "threshold options.entity_id is the monitored source"
                    ),
                    metadata={
                        "lower": options.get("lower"),
                        "upper": options.get("upper"),
                        "hysteresis": options.get("hysteresis"),
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
