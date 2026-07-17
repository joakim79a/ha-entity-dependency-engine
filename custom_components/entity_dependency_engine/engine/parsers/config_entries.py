"""Parser for Home Assistant core.config_entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..model import (
    Confidence,
    Edge,
    Node,
    RelationType,
)
from .base import ParserResult
from .json_storage import read_storage_json


PARSER_NAME = "config_entries"
EXPECTED_STORAGE_KEY = "core.config_entries"


class ConfigEntriesFormatError(RuntimeError):
    """Raised when core.config_entries has an unsupported structure."""


def parse_config_entries(path: str | Path) -> ParserResult:
    """Parse all valid Home Assistant config entries into graph nodes."""
    payload = read_storage_json(path)

    storage_key = payload.get("key")
    if storage_key != EXPECTED_STORAGE_KEY:
        raise ConfigEntriesFormatError(
            f"Expected {EXPECTED_STORAGE_KEY!r}, got {storage_key!r}"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ConfigEntriesFormatError("Missing or invalid data object")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ConfigEntriesFormatError("Missing or invalid data.entries list")

    result = ParserResult()

    for index, item in enumerate(entries):
        source_path = f"data.entries[{index}]"

        if not isinstance(item, dict):
            result.warnings.append(f"{source_path}: skipped non-object entry")
            continue

        entry_id = item.get("entry_id")
        if not isinstance(entry_id, str) or not entry_id.strip():
            result.warnings.append(
                f"{source_path}: missing valid config entry id"
            )
            continue

        domain = item.get("domain")
        if not isinstance(domain, str) or not domain.strip():
            result.warnings.append(
                f"{source_path}: missing valid config entry domain"
            )
            continue

        result.nodes.append(
            Node(
                node_id=make_config_entry_node_id(entry_id),
                node_type="config_entry",
                name=_best_name(item),
                metadata=_build_metadata(item, source_path),
            )
        )

    return result


def build_entity_config_entry_edges(
    entity_nodes: list[Node],
    config_entry_nodes: list[Node],
) -> ParserResult:
    """Create entity -> config entry relationships."""
    result = ParserResult()
    config_entries = _config_entry_index(config_entry_nodes)

    for entity in entity_nodes:
        if entity.node_type != "entity":
            continue

        entry_id = entity.metadata.get("config_entry_id")
        if not isinstance(entry_id, str):
            continue

        target = config_entries.get(entry_id)
        if target is None:
            result.warnings.append(
                f"{entity.node_id}: references missing config entry {entry_id}"
            )
            continue

        result.edges.append(
            Edge(
                source_node_id=entity.node_id,
                target_node_id=target,
                relation_type=RelationType.BELONGS_TO_CONFIG_ENTRY,
                source_parser=PARSER_NAME,
                confidence=Confidence.CERTAIN,
                source_file="core.entity_registry + core.config_entries",
                source_path=str(entity.metadata.get("source_path", "")),
                explanation=(
                    "Entity registry config_entry_id matches config entry id"
                ),
            )
        )

    return result


def build_device_config_entry_edges(
    device_nodes: list[Node],
    config_entry_nodes: list[Node],
) -> ParserResult:
    """Create device -> config entry relationships."""
    result = ParserResult()
    config_entries = _config_entry_index(config_entry_nodes)

    for device in device_nodes:
        if device.node_type != "device":
            continue

        raw_entry_ids = device.metadata.get("config_entries")
        if raw_entry_ids is None:
            continue

        if not isinstance(raw_entry_ids, list):
            result.warnings.append(
                f"{device.node_id}: invalid config_entries metadata"
            )
            continue

        for entry_id in raw_entry_ids:
            if not isinstance(entry_id, str):
                result.warnings.append(
                    f"{device.node_id}: invalid config entry reference"
                )
                continue

            target = config_entries.get(entry_id)
            if target is None:
                result.warnings.append(
                    f"{device.node_id}: references missing config entry "
                    f"{entry_id}"
                )
                continue

            result.edges.append(
                Edge(
                    source_node_id=device.node_id,
                    target_node_id=target,
                    relation_type=RelationType.BELONGS_TO_CONFIG_ENTRY,
                    source_parser=PARSER_NAME,
                    confidence=Confidence.CERTAIN,
                    source_file="core.device_registry + core.config_entries",
                    source_path=str(device.metadata.get("source_path", "")),
                    explanation=(
                        "Device registry config_entries contains config entry id"
                    ),
                )
            )

    return result


def make_config_entry_node_id(entry_id: str) -> str:
    """Return a stable graph id for one Home Assistant config entry."""
    return f"config_entry:{entry_id}"


def _config_entry_index(nodes: list[Node]) -> dict[str, str]:
    return {
        str(node.metadata["entry_id"]): node.node_id
        for node in nodes
        if node.node_type == "config_entry"
        and isinstance(node.metadata.get("entry_id"), str)
    }


def _best_name(item: dict[str, Any]) -> str | None:
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()

    domain = item.get("domain")
    if isinstance(domain, str) and domain.strip():
        return domain.strip()

    return None


def _build_metadata(
    item: dict[str, Any],
    source_path: str,
) -> dict[str, Any]:
    keys = (
        "domain",
        "source",
        "title",
        "unique_id",
        "version",
        "minor_version",
        "disabled_by",
        "pref_disable_new_entities",
        "pref_disable_polling",
        "created_at",
        "modified_at",
    )

    metadata = {
        key: item.get(key)
        for key in keys
        if item.get(key) is not None
    }

    metadata.update(
        {
            "entry_id": item["entry_id"],
            "source_parser": PARSER_NAME,
            "source_file": EXPECTED_STORAGE_KEY,
            "source_path": source_path,
        }
    )

    return metadata
