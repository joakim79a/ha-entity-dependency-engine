"""One-step graph expansion helpers for the visual panel."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Literal

from .graph import DirectedGraph
from .panel_graph import (
    ABSOLUTE_MAX_NODES,
    DEFAULT_MAX_NODES,
    SCHEMA_VERSION,
    _cyclic_components,
    _display_name,
    _graph_revision,
    _node_filter,
    _serialize_edges,
    _serialize_node,
    _traverse_filtered,
)

ExpansionDirection = Literal["parents", "children"]
VALID_EXPANSION_DIRECTIONS: frozenset[str] = frozenset(
    {"parents", "children"}
)


def expand_panel_graph(
    graph: DirectedGraph,
    root_id: str,
    node_id: str,
    *,
    direction: ExpansionDirection,
    visible_node_ids: Iterable[str],
    max_nodes: int = DEFAULT_MAX_NODES,
    absolute_max_nodes: int = ABSOLUTE_MAX_NODES,
    include_structural: bool = False,
    runtime_entities: Mapping[str, Mapping[str, Any]] | None = None,
    revision: str | None = None,
    warnings: Iterable[str] = (),
) -> dict[str, Any]:
    """Expand one visible node and return the complete merged panel graph."""
    graph.require_node(root_id)
    graph.require_node(node_id)

    if direction not in VALID_EXPANSION_DIRECTIONS:
        raise ValueError(f"Unsupported expansion direction: {direction}")
    if max_nodes < 1:
        raise ValueError("max_nodes must be at least 1")
    if absolute_max_nodes < 1:
        raise ValueError("absolute_max_nodes must be at least 1")

    runtime_entities = runtime_entities or {}
    node_allowed = _node_filter(
        graph,
        include_structural=include_structural,
    )

    ordered_visible = _validated_visible_nodes(
        graph,
        visible_node_ids,
        node_allowed=node_allowed,
    )
    visible_set = set(ordered_visible)

    if root_id not in visible_set:
        raise ValueError("root_id must be included in visible_node_ids")
    if node_id not in visible_set:
        raise ValueError("node_id must be included in visible_node_ids")

    effective_limit = min(max_nodes, absolute_max_nodes)
    if len(ordered_visible) > effective_limit:
        raise ValueError(
            "visible_node_ids already exceeds the requested node limit"
        )

    neighbours = (
        graph.parents(node_id)
        if direction == "parents"
        else graph.children(node_id)
    )
    eligible_neighbours = [
        neighbour
        for neighbour in neighbours
        if node_allowed(neighbour)
    ]
    eligible_neighbours.sort(
        key=lambda neighbour: (
            _display_name(
                graph.require_node(neighbour),
                runtime_entities.get(neighbour),
            ).casefold(),
            neighbour,
        )
    )

    missing_neighbours = [
        neighbour
        for neighbour in eligible_neighbours
        if neighbour not in visible_set
    ]
    available_slots = effective_limit - len(ordered_visible)
    added_node_ids = missing_neighbours[:available_slots]
    omitted_node_ids = missing_neighbours[available_slots:]

    selected_ids = [*ordered_visible, *added_node_ids]
    selected_set = set(selected_ids)

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
        candidate
        for candidate in graph.parents(root_id)
        if node_allowed(candidate)
    }
    direct_children = {
        candidate
        for candidate in graph.children(root_id)
        if node_allowed(candidate)
    }

    cyclic_components, cycle_node_ids = _cyclic_components(
        graph,
        node_allowed=node_allowed,
    )
    cycle_component_by_node = {
        candidate: component_index
        for component_index, component in enumerate(cyclic_components)
        for candidate in component
    }

    serialized_nodes = [
        _serialize_node(
            graph,
            candidate,
            root_id=root_id,
            selected_ids=selected_set,
            direct_parents=direct_parents,
            direct_children=direct_children,
            ancestors=ancestors,
            descendants=descendants,
            cycle_node_ids=cycle_node_ids,
            runtime=runtime_entities.get(candidate),
        )
        for candidate in selected_ids
    ]
    serialized_edges = _serialize_edges(
        graph,
        selected_set,
        cycle_component_by_node=cycle_component_by_node,
    )

    response_warnings = list(warnings)
    if max_nodes > absolute_max_nodes:
        response_warnings.append(
            "Requested node limit exceeded the absolute maximum and was "
            f"capped at {absolute_max_nodes}."
        )
    if omitted_node_ids:
        response_warnings.append(
            "Expansion truncated: "
            f"{len(omitted_node_ids)} neighbouring nodes were omitted."
        )

    broken_reference_count = sum(
        1 for node in serialized_nodes if node["broken"]
    )
    returned_cycle_components = {
        cycle_component_by_node[candidate]
        for candidate in selected_set
        if candidate in cycle_component_by_node
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "revision": revision or _graph_revision(graph),
        "root_id": root_id,
        "scope": "expanded",
        "limits": {
            "requested_max_nodes": max_nodes,
            "absolute_max_nodes": absolute_max_nodes,
        },
        "statistics": {
            "node_count": len(serialized_nodes),
            "edge_count": len(serialized_edges),
            "total_node_count": len(selected_ids) + len(omitted_node_ids),
            "omitted_node_count": len(omitted_node_ids),
            "broken_reference_count": broken_reference_count,
            "cycle_component_count": len(returned_cycle_components),
        },
        "truncated": bool(omitted_node_ids),
        "nodes": serialized_nodes,
        "edges": serialized_edges,
        "warnings": response_warnings,
        "expansion": {
            "node_id": node_id,
            "direction": direction,
            "added_node_ids": added_node_ids,
            "already_loaded": not missing_neighbours,
            "omitted_node_count": len(omitted_node_ids),
        },
    }


def _validated_visible_nodes(
    graph: DirectedGraph,
    visible_node_ids: Iterable[str],
    *,
    node_allowed,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for node_id in visible_node_ids:
        if node_id in seen:
            continue
        graph.require_node(node_id)
        if not node_allowed(node_id):
            raise ValueError(
                f"Visible node {node_id!r} is excluded by the node filter"
            )
        ordered.append(node_id)
        seen.add(node_id)

    if not ordered:
        raise ValueError("visible_node_ids must contain at least one node")

    return ordered
