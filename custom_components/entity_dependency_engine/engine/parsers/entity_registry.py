from __future__ import annotations
from pathlib import Path
from typing import Any

from ..model import Node
from .base import ParserResult
from .json_storage import read_storage_json

PARSER_NAME = "entity_registry"
EXPECTED_STORAGE_KEY = "core.entity_registry"

class EntityRegistryFormatError(RuntimeError):
    pass

def parse_entity_registry(path: str | Path) -> ParserResult:
    payload = read_storage_json(path)

    storage_key = payload.get("key")
    if storage_key != EXPECTED_STORAGE_KEY:
        raise EntityRegistryFormatError(
            f"Expected {EXPECTED_STORAGE_KEY!r}, got {storage_key!r}"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise EntityRegistryFormatError("Missing or invalid data object")

    entities = data.get("entities")
    if not isinstance(entities, list):
        raise EntityRegistryFormatError("Missing or invalid data.entities list")

    result = ParserResult()

    for index, item in enumerate(entities):
        source_path = f"data.entities[{index}]"

        if not isinstance(item, dict):
            result.warnings.append(f"{source_path}: skipped non-object entry")
            continue

        entity_id = item.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id.strip():
            result.warnings.append(f"{source_path}: missing valid entity_id")
            continue

        domain = entity_id.split(".", 1)[0] if "." in entity_id else "unknown"

        result.nodes.append(
            Node(
                node_id=entity_id,
                node_type="entity",
                name=_best_name(item),
                metadata={
                    "domain": domain,
                    **_build_metadata(item, source_path),
                },
            )
        )

    return result

def _best_name(item: dict[str, Any]) -> str | None:
    for key in ("name", "original_name", "suggested_object_id"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def _build_metadata(item: dict[str, Any], source_path: str) -> dict[str, Any]:
    keys = (
        "id", "unique_id", "platform", "device_id", "config_entry_id",
        "config_subentry_id", "area_id", "disabled_by", "hidden_by",
        "entity_category", "device_class", "original_device_class",
        "unit_of_measurement", "labels", "aliases", "translation_key",
        "created_at", "modified_at",
    )
    metadata = {key: item.get(key) for key in keys if item.get(key) is not None}
    metadata.update({
        "source_parser": PARSER_NAME,
        "source_file": EXPECTED_STORAGE_KEY,
        "source_path": source_path,
    })
    return metadata
