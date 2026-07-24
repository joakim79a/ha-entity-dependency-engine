"""Serialize dependency graphs for the visual Home Assistant panel.

This module is intentionally independent from Home Assistant. Runtime state and
friendly-name data can be supplied as an optional enrichment mapping by the
integration layer later.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from hashlib import sha256
from typing import Any, Literal

from .graph import DirectedGraph
from .model import Edge, Node, RelationType

GraphScope = Literal["direct", "all_parents", "all_children", "all"]

SCHEMA_VERSION = 1
DEFAULT_MAX_NODES = 250
ABSOLUTE_MAX_NODES = 1000
VALID_SCOPES: frozenset[str] = frozenset(
    {"direct", "all_parents", "all_children", "all"}
)

_STRUCTURAL_NODE_TYPES = frozenset({"device", "config_entry", "area"})
_STRUCTURAL_RELATIONS = frozenset(
    {
        RelationType.BELONGS_TO_DEVICE,
        RelationType.BELONGS_TO_CONFIG_ENTRY,
        RelationType.BELONGS_TO_AREA,
    }
)

_RELATION_LABELS: Mapping[RelationType, str] = {
    RelationType.READS: "Reads",
    RelationType.WRITES: "Writes",
    RelationType.TRIGGERS: "Triggers",
    RelationType.CALLS_SCRIPT: "Calls script",
    RelationType.CREATES: "Creates",
    RelationType.BELONGS_TO_DEVICE: "Belongs to device",
    RelationType.BELONGS_TO_CONFIG_ENTRY: "Belongs to config entry",
    RelationType.BELONGS_TO_AREA: "Belongs to area",
    RelationType.USES_BLUEPRINT: "Uses blueprint",
    RelationType.DISPLAYED_IN: "Displayed in",
    RelationType.MEMBER_OF: "Member of",
    RelationType.SOURCE_OF: "Source of",
    RelationType.DEPENDS_ON: "Depends on",
    RelationType.REFERENCES: "References",
}


def serialize_panel_graph(
    graph: DirectedGraph,
    root_id: str,
    *,
    scope: GraphScope = "direct",
    max_nodes: int = DEFAULT_MAX_NODES,
    absolute_max_nodes: int = ABSOLUTE_MAX_NODES,
    include_structural: bool = False,
    runtime_entities: Mapping[str, Mapping[str, Any]] | None = None,
    revision: str | None = None,
    warnings: Iterable[str] = (),
) -> dict[str, Any]:
    """Return a deterministic panel graph matching schema version 1.

    Edges always point from an upstream dependency (parent) to a downstream
    dependant (child). The root is returned once even if cycles make it
    reachable in both directions.
    """
    graph.require_node(root_id)
    _validate_limits(max_nodes, absolute_max_nodes)

    if scope not in VALID_SCOPES:
        raise ValueError(f"Unsupported graph scope: {scope}")

    runtime_entities = runtime_entities or {}
    response_warnings = list(warnings)
    effective_limit = min(max_nodes, absolute_max_nodes)

    if max_nodes > absolute_max_nodes:
        response_warnings.append(
            "Requested node limit exceeded the absolute maximum and was capped "
            f"at {absolute_max_nodes}."
        )

    node_allowed = _node_filter(graph, include_structural=include_structural)
    ancestors = _traverse_filtered(
        graph,
        root_id,
        direction="incoming",
        node_allowed=node_allowed,
    )
    descendants = _traverse_filtered(
        graph,
        root_id,
        direction="outgoing",
        node_allowed=node_allowed,
    )

    direct_parents = {
        node_id for node_id in graph.parents(root_id) if node_allowed(node_id)
    }
    direct_children = {
        node_id for node_id in graph.children(root_id) if node_allowed(node_id)
    }

    complete_ids = _scope_node_ids(
        root_id,
        scope=scope,
        direct_parents=direct_parents,
        direct_children=direct_children,
        ancestors=ancestors,
        descendants=descendants,
    )
    ordered_ids = _ordered_node_ids(
        graph,
        root_id,
        scope=scope,
        direct_parents=direct_parents,
        direct_children=direct_children,
        ancestors=ancestors,
        descendants=descendants,
        runtime_entities=runtime_entities,
    )
    selected_ids = ordered_ids[:effective_limit]
    selected_set = set(selected_ids)

    cyclic_components, cycle_node_ids = _cyclic_components(
        graph,
        node_allowed=node_allowed,
    )
    cycle_component_by_node = {
        node_id: component_index
        for component_index, component in enumerate(cyclic_components)
        for node_id in component
    }

    serialized_edges = _serialize_edges(
        graph,
        selected_set,
        cycle_component_by_node=cycle_component_by_node,
    )
    serialized_nodes = [
        _serialize_node(
            graph,
            node_id,
            root_id=root_id,
            selected_ids=selected_set,
            direct_parents=direct_parents,
            direct_children=direct_children,
            ancestors=ancestors,
            descendants=descendants,
            cycle_node_ids=cycle_node_ids,
            runtime=runtime_entities.get(node_id),
        )
        for node_id in selected_ids
    ]

    omitted_node_count = len(complete_ids) - len(selected_ids)
    truncated = omitted_node_count > 0
    if truncated:
        response_warnings.append(
            f"Graph truncated: returned {len(selected_ids)} of "
            f"{len(complete_ids)} reachable nodes."
        )

    broken_reference_count = sum(
        1 for node in serialized_nodes if node["broken"]
    )
    returned_cycle_components = {
        cycle_component_by_node[node_id]
        for node_id in selected_set
        if node_id in cycle_component_by_node
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "revision": revision or _graph_revision(graph),
        "root_id": root_id,
        "scope": scope,
        "limits": {
            "requested_max_nodes": max_nodes,
            "absolute_max_nodes": absolute_max_nodes,
        },
        "statistics": {
            "node_count": len(serialized_nodes),
            "edge_count": len(serialized_edges),
            "total_node_count": len(complete_ids),
            "omitted_node_count": omitted_node_count,
            "broken_reference_count": broken_reference_count,
            "cycle_component_count": len(returned_cycle_components),
        },
        "truncated": truncated,
        "nodes": serialized_nodes,
        "edges": serialized_edges,
        "warnings": response_warnings,
    }


def _validate_limits(max_nodes: int, absolute_max_nodes: int) -> None:
    if max_nodes < 1:
        raise ValueError("max_nodes must be at least 1")
    if absolute_max_nodes < 1:
        raise ValueError("absolute_max_nodes must be at least 1")


def _node_filter(
    graph: DirectedGraph,
    *,
    include_structural: bool,
):
    def allowed(node_id: str) -> bool:
        node = graph.require_node(node_id)
        return include_structural or not _is_structural_node(node)

    return allowed


def _traverse_filtered(
    graph: DirectedGraph,
    root_id: str,
    *,
    direction: Literal["incoming", "outgoing"],
    node_allowed,
) -> dict[str, int]:
    visited: dict[str, int] = {root_id: 0}
    queue: deque[str] = deque([root_id])

    while queue:
        current = queue.popleft()
        next_depth = visited[current] + 1
        neighbours = (
            graph.parents(current)
            if direction == "incoming"
            else graph.children(current)
        )

        for neighbour in sorted(neighbours):
            if neighbour in visited or not node_allowed(neighbour):
                continue
            visited[neighbour] = next_depth
            queue.append(neighbour)

    visited.pop(root_id)
    return visited


def _scope_node_ids(
    root_id: str,
    *,
    scope: GraphScope,
    direct_parents: set[str],
    direct_children: set[str],
    ancestors: Mapping[str, int],
    descendants: Mapping[str, int],
) -> set[str]:
    if scope == "direct":
        return {root_id, *direct_parents, *direct_children}
    if scope == "all_parents":
        return {root_id, *ancestors}
    if scope == "all_children":
        return {root_id, *descendants}
    return {root_id, *ancestors, *descendants}


def _ordered_node_ids(
    graph: DirectedGraph,
    root_id: str,
    *,
    scope: GraphScope,
    direct_parents: set[str],
    direct_children: set[str],
    ancestors: Mapping[str, int],
    descendants: Mapping[str, int],
    runtime_entities: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    def sorted_ids(node_ids: Iterable[str]) -> list[str]:
        return sorted(
            node_ids,
            key=lambda node_id: (
                _display_name(
                    graph.require_node(node_id),
                    runtime_entities.get(node_id),
                ).casefold(),
                node_id,
            ),
        )

    if scope == "direct":
        tail = _interleave(
            sorted_ids(direct_parents),
            sorted_ids(direct_children),
        )
        return _deduplicate([root_id, *tail])

    if scope == "all_parents":
        return [
            root_id,
            *sorted(
                ancestors,
                key=lambda node_id: (
                    ancestors[node_id],
                    _display_name(
                        graph.require_node(node_id),
                        runtime_entities.get(node_id),
                    ).casefold(),
                    node_id,
                ),
            ),
        ]

    if scope == "all_children":
        return [
            root_id,
            *sorted(
                descendants,
                key=lambda node_id: (
                    descendants[node_id],
                    _display_name(
                        graph.require_node(node_id),
                        runtime_entities.get(node_id),
                    ).casefold(),
                    node_id,
                ),
            ),
        ]

    upstream_layers = _depth_layers(ancestors, sorted_ids)
    downstream_layers = _depth_layers(descendants, sorted_ids)
    ordered: list[str] = [root_id]
    max_depth = max(
        max(upstream_layers, default=0),
        max(downstream_layers, default=0),
    )
    for depth in range(1, max_depth + 1):
        ordered.extend(
            _interleave(
                upstream_layers.get(depth, []),
                downstream_layers.get(depth, []),
            )
        )
    return _deduplicate(ordered)


def _depth_layers(
    depths: Mapping[str, int],
    sorter,
) -> dict[int, list[str]]:
    layers: dict[int, list[str]] = {}
    for node_id, depth in depths.items():
        layers.setdefault(depth, []).append(node_id)
    return {depth: sorter(node_ids) for depth, node_ids in layers.items()}


def _interleave(left: list[str], right: list[str]) -> list[str]:
    result: list[str] = []
    max_length = max(len(left), len(right), 0)
    for index in range(max_length):
        if index < len(left):
            result.append(left[index])
        if index < len(right):
            result.append(right[index])
    return result


def _deduplicate(node_ids: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(node_ids))


def _serialize_node(
    graph: DirectedGraph,
    node_id: str,
    *,
    root_id: str,
    selected_ids: set[str],
    direct_parents: set[str],
    direct_children: set[str],
    ancestors: Mapping[str, int],
    descendants: Mapping[str, int],
    cycle_node_ids: set[str],
    runtime: Mapping[str, Any] | None,
) -> dict[str, Any]:
    node = graph.require_node(node_id)
    parents = graph.parents(node_id)
    children = graph.children(node_id)
    roles: list[str] = []

    if node_id == root_id:
        roles.append("root")
    if node_id in direct_parents:
        roles.append("parent")
    elif node_id in ancestors:
        roles.append("ancestor")
    if node_id in direct_children:
        roles.append("child")
    elif node_id in descendants:
        roles.append("descendant")

    return {
        "id": node_id,
        "node_type": node.node_type,
        "name": node.name,
        "display_name": _display_name(node, runtime),
        "domain": _domain(node),
        "roles": roles,
        "upstream_depth": ancestors.get(node_id),
        "downstream_depth": descendants.get(node_id),
        "parent_count": len(parents),
        "child_count": len(children),
        "parents_loaded": parents.issubset(selected_ids),
        "children_loaded": children.issubset(selected_ids),
        "expandable_upstream": bool(parents),
        "expandable_downstream": bool(children),
        "broken": _is_broken_node(node),
        "in_cycle": node_id in cycle_node_ids,
        "structural": _is_structural_node(node),
        "runtime": _runtime_payload(runtime),
        "context": _context_payload(node, runtime),
    }


def _serialize_edges(
    graph: DirectedGraph,
    selected_ids: set[str],
    *,
    cycle_component_by_node: Mapping[str, int],
) -> list[dict[str, Any]]:
    public_edges: dict[tuple[str, ...], dict[str, Any]] = {}

    for edge in graph.iter_edges():
        if (
            edge.source_node_id not in selected_ids
            or edge.target_node_id not in selected_ids
        ):
            continue

        source_node = graph.require_node(edge.source_node_id)
        target_node = graph.require_node(edge.target_node_id)
        structural = (
            _is_structural_node(source_node)
            or _is_structural_node(target_node)
            or edge.relation_type in _STRUCTURAL_RELATIONS
        )
        cycle_edge = (
            edge.source_node_id in cycle_component_by_node
            and cycle_component_by_node.get(edge.source_node_id)
            == cycle_component_by_node.get(edge.target_node_id)
        )
        public_key = (
            edge.source_node_id,
            edge.target_node_id,
            edge.relation_type.value,
            edge.source_parser,
            edge.confidence.value,
            str(structural),
            str(cycle_edge),
        )
        edge_id = "edge-" + sha256(
            "\x1f".join(public_key).encode("utf-8")
        ).hexdigest()[:12]
        public_edges[public_key] = {
            "id": edge_id,
            "source": edge.source_node_id,
            "target": edge.target_node_id,
            "relation": edge.relation_type.value,
            "source_parser": edge.source_parser,
            "confidence": edge.confidence.value,
            "label": _RELATION_LABELS.get(
                edge.relation_type,
                edge.relation_type.value.replace("_", " ").capitalize(),
            ),
            "structural": structural,
            "cycle_edge": cycle_edge,
        }

    return [public_edges[key] for key in sorted(public_edges)]


def _display_name(
    node: Node,
    runtime: Mapping[str, Any] | None,
) -> str:
    if runtime:
        for key in ("friendly_name", "name", "registry_name"):
            value = runtime.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if node.name and node.name.strip():
        return node.name.strip()
    return node.node_id


def _domain(node: Node) -> str | None:
    value = node.metadata.get("domain")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if "." in node.node_id and node.node_type in {
        "entity",
        "automation",
        "script",
        "unknown_entity",
    }:
        return node.node_id.split(".", 1)[0]
    return None


def _runtime_payload(runtime: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if runtime is None:
        return None

    state = _optional_string(runtime.get("state"))
    state_display = _optional_string(runtime.get("state_display"))
    icon = _optional_string(runtime.get("icon"))
    available_value = runtime.get("available")
    if isinstance(available_value, bool):
        available = available_value
    else:
        available = state not in {None, "unknown", "unavailable"}

    return {
        "state": state,
        "state_display": state_display,
        "available": available,
        "icon": icon,
    }


def _context_payload(
    node: Node,
    runtime: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    runtime = runtime or {}
    values = {
        "platform": _optional_string(node.metadata.get("platform")),
        "device_id": _optional_string(node.metadata.get("device_id")),
        "device_name": _optional_string(runtime.get("device_name")),
        "area_id": _optional_string(node.metadata.get("area_id")),
        "area_name": _optional_string(runtime.get("area_name")),
        "config_entry_id": _optional_string(
            node.metadata.get("config_entry_id")
        ),
        "integration": _optional_string(runtime.get("integration"))
        or _optional_string(node.metadata.get("platform")),
    }
    return values if any(value is not None for value in values.values()) else None


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _is_structural_node(node: Node) -> bool:
    return node.node_type in _STRUCTURAL_NODE_TYPES or bool(
        node.metadata.get("structural", False)
    )


def _is_broken_node(node: Node) -> bool:
    return node.node_type in {"unknown", "unknown_entity"} or bool(
        node.metadata.get("broken", False)
    )


def _graph_revision(graph: DirectedGraph) -> str:
    digest = sha256()
    for node in sorted(
        graph.iter_nodes(),
        key=lambda item: item.node_id,
    ):
        digest.update(
            "\x1f".join(
                (node.node_id, node.node_type, node.name or "")
            ).encode("utf-8")
        )
        digest.update(b"\x1e")
    for edge in sorted(
        graph.iter_edges(),
        key=_edge_sort_key,
    ):
        digest.update("\x1f".join(_edge_sort_key(edge)).encode("utf-8"))
        digest.update(b"\x1e")
    return digest.hexdigest()[:16]


def _edge_sort_key(edge: Edge) -> tuple[str, ...]:
    return (
        edge.source_node_id,
        edge.target_node_id,
        edge.relation_type.value,
        edge.source_parser,
        edge.confidence.value,
        edge.source_file or "",
        edge.source_path or "",
        edge.explanation or "",
    )


def _cyclic_components(
    graph: DirectedGraph,
    *,
    node_allowed,
) -> tuple[list[frozenset[str]], set[str]]:
    """Return cyclic strongly connected components using Tarjan's algorithm."""
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[frozenset[str]] = []

    def strong_connect(node_id: str) -> None:
        nonlocal index
        indices[node_id] = index
        lowlinks[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)

        for child_id in sorted(graph.children(node_id)):
            if not node_allowed(child_id):
                continue
            if child_id not in indices:
                strong_connect(child_id)
                lowlinks[node_id] = min(
                    lowlinks[node_id], lowlinks[child_id]
                )
            elif child_id in on_stack:
                lowlinks[node_id] = min(
                    lowlinks[node_id], indices[child_id]
                )

        if lowlinks[node_id] != indices[node_id]:
            return

        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node_id:
                break

        component_set = frozenset(component)
        is_self_cycle = (
            len(component_set) == 1
            and node_id in graph.children(node_id)
        )
        if len(component_set) > 1 or is_self_cycle:
            components.append(component_set)

    for node in sorted(graph.iter_nodes(), key=lambda item: item.node_id):
        if not node_allowed(node.node_id) or node.node_id in indices:
            continue
        strong_connect(node.node_id)

    components.sort(key=lambda component: tuple(sorted(component)))
    return components, set().union(*components) if components else set()
