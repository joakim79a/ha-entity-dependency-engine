"""Parser for Home Assistant scripts.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

from ..model import Confidence, Edge, Node, RelationType
from .base import ParserResult
from .template_references import (
    extract_template_references,
)


PARSER_NAME = "scripts"
SOURCE_FILE = "scripts.yaml"
SERVICE_KEYS = {"action", "service"}


class ScriptsFormatError(RuntimeError):
    """Raised when scripts.yaml has an unsupported structure."""


def parse_script_relations(
    scripts_path: str | Path,
    entity_nodes: list[Node],
) -> ParserResult:
    """Parse script definitions into incoming and outgoing dependency edges."""
    path = Path(scripts_path)

    if not path.exists():
        return ParserResult(
            warnings=[f"{SOURCE_FILE}: file not found: {path}"]
        )

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ScriptsFormatError(
            f"Could not parse {path}: {exc}"
        ) from exc

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        raise ScriptsFormatError(
            f"Expected top-level object in {path}, "
            f"got {type(payload).__name__}"
        )

    script_entities = {
        node.node_id
        for node in entity_nodes
        if node.node_type == "entity"
        and node.metadata.get("platform") == "script"
    }
    known_entity_ids = {
        node.node_id for node in entity_nodes if node.node_type == "entity"
    }

    result = ParserResult()

    for object_id, definition in payload.items():
        source_path = str(object_id)

        if not isinstance(object_id, str):
            result.warnings.append(
                f"{source_path}: invalid script object id"
            )
            continue

        if not isinstance(definition, dict):
            result.warnings.append(
                f"{source_path}: skipped non-object script"
            )
            continue

        script_entity_id = f"script.{object_id}"

        if script_entity_id not in script_entities:
            result.warnings.append(
                f"{source_path}: no script entity found for {script_entity_id}"
            )
            continue

        sequence = definition.get("sequence", [])

        _parse_sequence(
            result=result,
            value=sequence,
            script_entity_id=script_entity_id,
            known_entity_ids=known_entity_ids,
            source_path=f"{source_path}.sequence",
        )

    return result


def _parse_sequence(
    *,
    result: ParserResult,
    value: Any,
    script_entity_id: str,
    known_entity_ids: set[str],
    source_path: str,
) -> None:
    for item, item_path in _walk(value, source_path):
        if not isinstance(item, dict):
            continue

        targets = _extract_target_entity_ids(item, item_path)

        for entity_id, ref_path in targets:
            relation_type = (
                RelationType.CALLS_SCRIPT
                if entity_id.startswith("script.")
                else RelationType.WRITES
            )

            _append_edge(
                result=result,
                source_node_id=script_entity_id,
                target_node_id=entity_id,
                relation_type=relation_type,
                confidence=Confidence.CERTAIN,
                known_entity_ids=known_entity_ids,
                source_path=ref_path,
                explanation="script action target",
            )

        references = _collect_references(item, item_path)
        targeted = {entity_id for entity_id, _ in targets}

        for entity_id, confidence, ref_path, explanation in references:
            if entity_id in targeted:
                continue

            _append_edge(
                result=result,
                source_node_id=entity_id,
                target_node_id=script_entity_id,
                relation_type=RelationType.READS,
                confidence=confidence,
                known_entity_ids=known_entity_ids,
                source_path=ref_path,
                explanation=f"script input: {explanation}",
            )


def _collect_references(
    value: Any,
    source_path: str,
) -> list[tuple[str, Confidence, str, str]]:
    found: dict[tuple[str, Confidence, str], str] = {}

    for item, item_path, parent_key in _walk_with_key(value, source_path):
        if isinstance(item, str):
            if parent_key in SERVICE_KEYS:
                continue

            refs = extract_template_references(item)

            for entity_id in refs.certain:
                found[
                    (entity_id, Confidence.CERTAIN, item_path)
                ] = "static template reference"

            for entity_id in refs.probable:
                found[
                    (entity_id, Confidence.PROBABLE, item_path)
                ] = "plain entity-id token"

        elif isinstance(item, dict):
            for key in ("entity_id", "entity", "entities"):
                if key not in item:
                    continue

                for entity_id in _normalize_entity_ids(item[key]):
                    found[
                        (
                            entity_id,
                            Confidence.CERTAIN,
                            f"{item_path}.{key}",
                        )
                    ] = f"{key} reference"

    return [
        (entity_id, confidence, path, explanation)
        for (entity_id, confidence, path), explanation in found.items()
    ]


def _extract_target_entity_ids(
    item: dict[str, Any],
    item_path: str,
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    target = item.get("target")
    if isinstance(target, dict) and "entity_id" in target:
        for entity_id in _normalize_entity_ids(target["entity_id"]):
            found.append((entity_id, f"{item_path}.target.entity_id"))

    if "entity_id" in item and _looks_like_action(item):
        for entity_id in _normalize_entity_ids(item["entity_id"]):
            found.append((entity_id, f"{item_path}.entity_id"))

    action_name = item.get("action", item.get("service"))
    if isinstance(action_name, str) and action_name.startswith("script."):
        found.append((action_name, f"{item_path}.action"))

    return found


def _looks_like_action(item: dict[str, Any]) -> bool:
    return any(
        key in item
        for key in (
            "action",
            "service",
            "target",
            "delay",
            "wait_template",
            "wait_for_trigger",
            "choose",
            "if",
            "repeat",
            "parallel",
            "event",
            "stop",
        )
    )


def _normalize_entity_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        if "{{" in value or "{%" in value:
            return []
        return [value] if "." in value else []

    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_normalize_entity_ids(item))
        return result

    return []


def _walk(value: Any, path: str) -> Iterable[tuple[Any, str]]:
    yield value, path

    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _walk_with_key(
    value: Any,
    path: str,
    parent_key: str | None = None,
) -> Iterable[tuple[Any, str, str | None]]:
    yield value, path, parent_key

    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_with_key(child, f"{path}.{key}", str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_with_key(child, f"{path}[{index}]", parent_key)


def _append_edge(
    *,
    result: ParserResult,
    source_node_id: str,
    target_node_id: str,
    relation_type: RelationType,
    confidence: Confidence,
    known_entity_ids: set[str],
    source_path: str,
    explanation: str,
) -> None:
    unknown_id = (
        source_node_id
        if source_node_id not in known_entity_ids
        else target_node_id
        if target_node_id not in known_entity_ids
        else None
    )

    if unknown_id is not None:
        result.warnings.append(
            f"{source_path}: script relation references unknown entity "
            f"{unknown_id}"
        )

    result.edges.append(
        Edge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            source_parser=PARSER_NAME,
            confidence=confidence,
            source_file=SOURCE_FILE,
            source_path=source_path,
            explanation=explanation,
        )
    )
