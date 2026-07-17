"""Parser for GUI-created template entities in core.config_entries."""

from __future__ import annotations

from collections.abc import Iterable
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
from .template_references import (
    extract_template_references,
)


PARSER_NAME = "gui_templates"
EXPECTED_STORAGE_KEY = "core.config_entries"
TEMPLATE_DOMAIN = "template"

TEMPLATE_OPTION_KEYS = {
    "state",
    "availability",
    "icon",
    "picture",
    "attributes",
    "state_attributes",
    "turn_on",
    "turn_off",
    "set_value",
    "press",
    "select_option",
    "level",
    "temperature",
    "percentage",
    "hs",
    "rgb",
    "rgbw",
    "rgbww",
    "effect",
}


class GuiTemplateFormatError(RuntimeError):
    """Raised when core.config_entries has an unsupported structure."""


def parse_gui_template_relations(
    config_entries_path: str | Path,
    entity_nodes: list[Node],
) -> ParserResult:
    """Create source-entity -> GUI-template-entity relations."""
    payload = read_storage_json(config_entries_path)

    if payload.get("key") != EXPECTED_STORAGE_KEY:
        raise GuiTemplateFormatError(
            f"Expected {EXPECTED_STORAGE_KEY!r}, got {payload.get('key')!r}"
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise GuiTemplateFormatError("Missing or invalid data object")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise GuiTemplateFormatError("Missing or invalid data.entries list")

    entity_by_config_entry = _entity_index_by_config_entry(entity_nodes)
    known_entity_ids = {
        node.node_id for node in entity_nodes if node.node_type == "entity"
    }
    known_domains = {
        entity_id.split(".", 1)[0]
        for entity_id in known_entity_ids
        if "." in entity_id
    }

    result = ParserResult()

    for index, entry in enumerate(entries):
        source_path = f"data.entries[{index}]"

        if not isinstance(entry, dict):
            continue
        if entry.get("domain") != TEMPLATE_DOMAIN:
            continue

        entry_id = entry.get("entry_id")
        if not isinstance(entry_id, str):
            result.warnings.append(
                f"{source_path}: template entry missing entry_id"
            )
            continue

        targets = entity_by_config_entry.get(entry_id, [])
        if not targets:
            result.warnings.append(
                f"{source_path}: no entity found for template config entry "
                f"{entry_id}"
            )
            continue

        if len(targets) > 1:
            result.warnings.append(
                f"{source_path}: template config entry {entry_id} maps to "
                f"{len(targets)} entities"
            )

        options = entry.get("options")
        if not isinstance(options, dict):
            result.warnings.append(
                f"{source_path}: template entry has invalid options"
            )
            continue

        template_strings = list(_iter_template_strings(options))

        for target in targets:
            seen_edges: set[tuple[str, Confidence, str]] = set()

            for option_path, template_text in template_strings:
                references = extract_template_references(template_text)

                for source_entity_id in references.certain:
                    key = (
                        source_entity_id,
                        Confidence.CERTAIN,
                        option_path,
                    )
                    if key in seen_edges:
                        continue
                    seen_edges.add(key)

                    _append_relation(
                        result=result,
                        source_entity_id=source_entity_id,
                        target_entity_id=target.node_id,
                        confidence=Confidence.CERTAIN,
                        known_entity_ids=known_entity_ids,
                        known_domains=known_domains,
                        source_path=f"{source_path}.options.{option_path}",
                        explanation=(
                            "Static entity reference found in GUI template"
                        ),
                    )

                for source_entity_id in references.probable:
                    key = (
                        source_entity_id,
                        Confidence.PROBABLE,
                        option_path,
                    )
                    if key in seen_edges:
                        continue
                    seen_edges.add(key)

                    _append_relation(
                        result=result,
                        source_entity_id=source_entity_id,
                        target_entity_id=target.node_id,
                        confidence=Confidence.PROBABLE,
                        known_entity_ids=known_entity_ids,
                        known_domains=known_domains,
                        source_path=f"{source_path}.options.{option_path}",
                        explanation=(
                            "Plain entity-id token found in GUI template"
                        ),
                    )

    return result


def _append_relation(
    *,
    result: ParserResult,
    source_entity_id: str,
    target_entity_id: str,
    confidence: Confidence,
    known_entity_ids: set[str],
    known_domains: set[str],
    source_path: str,
    explanation: str,
) -> None:
    is_known = source_entity_id in known_entity_ids
    domain = source_entity_id.split(".", 1)[0]

    # Probable matches such as states.sensor or ns.total_value are usually
    # Jinja object/namespace attributes, not entity IDs. Keep probable unknown
    # references only when their domain is a real HA entity domain present in
    # this installation. This preserves warnings for broken sensor.*, switch.*,
    # etc. references while removing parser noise.
    if (
        confidence is Confidence.PROBABLE
        and not is_known
        and domain not in known_domains
    ):
        return

    if not is_known:
        result.warnings.append(
            f"{source_path}: template {target_entity_id} references unknown "
            f"entity {source_entity_id}"
        )

    result.edges.append(
        Edge(
            source_node_id=source_entity_id,
            target_node_id=target_entity_id,
            relation_type=RelationType.SOURCE_OF,
            source_parser=PARSER_NAME,
            confidence=confidence,
            source_file=EXPECTED_STORAGE_KEY,
            source_path=source_path,
            explanation=explanation,
        )
    )


def _entity_index_by_config_entry(
    entity_nodes: Iterable[Node],
) -> dict[str, list[Node]]:
    index: dict[str, list[Node]] = {}

    for node in entity_nodes:
        if node.node_type != "entity":
            continue

        entry_id = node.metadata.get("config_entry_id")
        platform = node.metadata.get("platform")

        if not isinstance(entry_id, str) or platform != TEMPLATE_DOMAIN:
            continue

        index.setdefault(entry_id, []).append(node)

    return index


def _iter_template_strings(
    value: Any,
    path: str = "",
) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)

            if key in TEMPLATE_OPTION_KEYS:
                yield from _iter_all_strings(child, child_path)
            elif isinstance(child, (dict, list)):
                yield from _iter_template_strings(child, child_path)

    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from _iter_template_strings(child, child_path)


def _iter_all_strings(
    value: Any,
    path: str,
) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield from _iter_all_strings(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from _iter_all_strings(child, child_path)
