"""Parser for Home Assistant core.device_registry."""

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


PARSER_NAME = "device_registry"
EXPECTED_STORAGE_KEY = "core.device_registry"


class DeviceRegistryFormatError(RuntimeError):
    """Raised when core.device_registry has an unsupported structure."""


def parse_device_registry(path: str | Path) -> ParserResult:
    """Parse every valid Home Assistant device into normalized graph nodes."""
    payload = read_storage_json(path)

    storage_key = payload.get("key")
    if storage_key != EXPECTED_STORAGE_KEY:
        raise DeviceRegistryFormatError(
            f"Expected {EXPECTED_STORAGE_KEY!r}, got {storage_key!r}"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise DeviceRegistryFormatError("Missing or invalid data object")

    devices = data.get("devices")
    if not isinstance(devices, list):
        raise DeviceRegistryFormatError("Missing or invalid data.devices list")

    result = ParserResult()

    for index, item in enumerate(devices):
        source_path = f"data.devices[{index}]"

        if not isinstance(item, dict):
            result.warnings.append(f"{source_path}: skipped non-object entry")
            continue

        device_id = item.get("id")
        if not isinstance(device_id, str) or not device_id.strip():
            result.warnings.append(f"{source_path}: missing valid device id")
            continue

        node_id = make_device_node_id(device_id)

        result.nodes.append(
            Node(
                node_id=node_id,
                node_type="device",
                name=_best_name(item),
                metadata=_build_metadata(item, source_path),
            )
        )

    return result


def build_entity_device_edges(
    entity_nodes: list[Node],
    device_nodes: list[Node],
) -> ParserResult:
    """Create entity -> device relationships from registry metadata."""
    result = ParserResult()
    device_ids = {
        node.metadata.get("registry_id"): node.node_id
        for node in device_nodes
        if node.node_type == "device"
        and isinstance(node.metadata.get("registry_id"), str)
    }

    for entity in entity_nodes:
        if entity.node_type != "entity":
            continue

        registry_device_id = entity.metadata.get("device_id")
        if not isinstance(registry_device_id, str):
            continue

        device_node_id = device_ids.get(registry_device_id)
        if device_node_id is None:
            result.warnings.append(
                f"{entity.node_id}: references missing device "
                f"{registry_device_id}"
            )
            continue

        result.edges.append(
            Edge(
                source_node_id=entity.node_id,
                target_node_id=device_node_id,
                relation_type=RelationType.BELONGS_TO_DEVICE,
                source_parser=PARSER_NAME,
                confidence=Confidence.CERTAIN,
                source_file="core.entity_registry + core.device_registry",
                source_path=str(entity.metadata.get("source_path", "")),
                explanation=(
                    "Entity registry device_id matches device registry id"
                ),
            )
        )

    return result


def make_device_node_id(registry_id: str) -> str:
    """Return a stable graph id for one Home Assistant device."""
    return f"device:{registry_id}"


def _best_name(item: dict[str, Any]) -> str | None:
    for key in ("name_by_user", "name", "model"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _build_metadata(
    item: dict[str, Any],
    source_path: str,
) -> dict[str, Any]:
    keys = (
        "area_id",
        "configuration_url",
        "disabled_by",
        "entry_type",
        "hw_version",
        "manufacturer",
        "model",
        "model_id",
        "name",
        "name_by_user",
        "primary_config_entry",
        "serial_number",
        "sw_version",
        "via_device_id",
        "created_at",
        "modified_at",
    )

    metadata = {
        key: item.get(key)
        for key in keys
        if item.get(key) is not None
    }

    config_entries = item.get("config_entries")
    if isinstance(config_entries, list):
        metadata["config_entries"] = list(config_entries)
    elif config_entries is not None:
        metadata["config_entries"] = config_entries

    identifiers = item.get("identifiers")
    if isinstance(identifiers, list):
        metadata["identifiers"] = list(identifiers)

    connections = item.get("connections")
    if isinstance(connections, list):
        metadata["connections"] = list(connections)

    metadata.update(
        {
            "registry_id": item["id"],
            "source_parser": PARSER_NAME,
            "source_file": EXPECTED_STORAGE_KEY,
            "source_path": source_path,
        }
    )

    return metadata
