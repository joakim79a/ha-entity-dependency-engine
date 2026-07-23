"""Pure backend helpers for the visual dependency panel."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from .builder import BuildResult, build_graph
from .graph import DirectedGraph
from .model import Node


_SEARCHABLE_NODE_TYPES = frozenset(
    {"entity", "automation", "script", "unknown_entity"}
)


@dataclass(slots=True)
class PanelGraphCache:
    """Thread-safe in-memory cache for the parsed Home Assistant graph."""

    _result: BuildResult | None = None
    _config_dir: Path | None = None
    _lock: Lock = field(default_factory=Lock)

    def get(
        self,
        config_dir: str | Path,
        *,
        refresh: bool = False,
    ) -> BuildResult:
        """Return a cached graph build, rebuilding when requested."""
        normalized_config_dir = Path(config_dir).resolve()

        with self._lock:
            if (
                refresh
                or self._result is None
                or self._config_dir != normalized_config_dir
            ):
                self._result = build_graph(normalized_config_dir)
                self._config_dir = normalized_config_dir

            return self._result

    def clear(self) -> None:
        """Discard the cached graph snapshot."""
        with self._lock:
            self._result = None
            self._config_dir = None


def search_graph_entities(
    graph: DirectedGraph,
    *,
    runtime_entities: Mapping[str, Mapping[str, Any]] | None = None,
    query: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Return deterministic entity search results for the panel."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    runtime_entities = runtime_entities or {}
    normalized_query = " ".join(query.casefold().split())
    matches: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    for node in graph.iter_nodes():
        if not _is_searchable_node(node):
            continue

        runtime = runtime_entities.get(node.node_id, {})
        display_name = _display_name(node, runtime)
        domain = _domain(node)
        platform = _optional_string(runtime.get("integration")) or _optional_string(
            node.metadata.get("platform")
        )
        device_name = _optional_string(runtime.get("device_name"))
        area_name = _optional_string(runtime.get("area_name"))

        searchable_values = [
            display_name,
            node.node_id,
            node.name or "",
            domain or "",
            platform or "",
            device_name or "",
            area_name or "",
        ]

        score = _search_score(normalized_query, searchable_values)
        if score is None:
            continue

        state = _optional_string(runtime.get("state"))
        state_display = _optional_string(runtime.get("state_display"))
        available_value = runtime.get("available")
        available = (
            available_value
            if isinstance(available_value, bool)
            else state not in {None, "unknown", "unavailable"}
        )

        result = {
            "entity_id": node.node_id,
            "display_name": display_name,
            "domain": domain,
            "icon": _optional_string(runtime.get("icon")),
            "state": state,
            "state_display": state_display,
            "available": available,
            "platform": platform,
            "device_name": device_name,
            "area_name": area_name,
            "parent_count": len(graph.parents(node.node_id)),
            "child_count": len(graph.children(node.node_id)),
            "broken": node.node_type in {"unknown", "unknown_entity"}
            or bool(node.metadata.get("broken", False)),
        }

        sort_key = (
            score,
            display_name.casefold(),
            node.node_id.casefold(),
        )
        matches.append((sort_key, result))

    matches.sort(key=lambda item: item[0])
    total = len(matches)

    return {
        "query": query,
        "count": min(total, limit),
        "total": total,
        "entities": [result for _, result in matches[:limit]],
    }


def _is_searchable_node(node: Node) -> bool:
    return node.node_type in _SEARCHABLE_NODE_TYPES or (
        "." in node.node_id
        and node.node_type not in {"device", "config_entry", "area"}
    )


def _search_score(
    query: str,
    values: list[str],
) -> int | None:
    if not query:
        return 4

    normalized = [value.casefold() for value in values if value]
    if any(value == query for value in normalized):
        return 0
    if any(value.startswith(query) for value in normalized):
        return 1

    query_terms = query.split()
    if all(any(term in value for value in normalized) for term in query_terms):
        return 2
    if any(query in value for value in normalized):
        return 3
    return None


def _display_name(node: Node, runtime: Mapping[str, Any]) -> str:
    for key in ("friendly_name", "name", "registry_name"):
        value = _optional_string(runtime.get(key))
        if value is not None:
            return value

    if node.name and node.name.strip():
        return node.name.strip()
    return node.node_id


def _domain(node: Node) -> str | None:
    value = _optional_string(node.metadata.get("domain"))
    if value is not None:
        return value
    if "." in node.node_id:
        return node.node_id.split(".", 1)[0]
    return None


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None

